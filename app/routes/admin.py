# Remove/Unregister User Route (must be after bp is defined)
# Move this route after the Blueprint definition below
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, current_app
from flask_login import login_required, current_user
from app import db, mail
from flask_mail import Message
from app.models.models import User, Election, Vote, Candidate
from app.models.query import Query
from app.utils.time_utils import convert_to_24hr, convert_to_12hr, get_date_string
from datetime import datetime
from functools import wraps
import csv
import logging
from io import StringIO, BytesIO
from pathlib import Path
import os
from werkzeug.utils import secure_filename

bp = Blueprint('admin', __name__, url_prefix='/admin')
logger = logging.getLogger(__name__)



@bp.app_template_filter('format_time')
def format_time(datetime_obj):
    """Format time in 12-hour format"""
    return convert_to_12hr(datetime_obj) if datetime_obj else ''

@bp.context_processor
def utility_processor():
    return { 
        'now': datetime.utcnow
    }

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You do not have permission to access this page')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/')
@login_required
@admin_required
def dashboard():
    """Admin dashboard with statistics and recent activity"""
    try:
        # Get statistics with error handling
        stats = {
            'total_users': 0,
            'total_elections': 0,
            'active_elections': 0,
            'total_votes': 0
        }
        
        try:
            stats['total_users'] = User.query.count()
            stats['total_elections'] = Election.query.count()
            stats['total_votes'] = Vote.query.count()
            
            # Get active elections (not ended and is_active)
            now = datetime.utcnow()
            stats['active_elections'] = Election.query.filter(
                Election.is_active == True,
                Election.end_date > now
            ).count()
        except Exception as e:
            logger.error(f"Error fetching dashboard statistics: {str(e)}")
        
        # Get recent data
        recent_data = {
            'elections': [],
            'users': []
        }
        
        try:
            recent_data['elections'] = Election.query\
                .order_by(Election.created_at.desc())\
                .limit(5)\
                .all()
            # Attach results for the most recent election (active or ended) for dashboard chart
            if recent_data['elections']:
                latest = recent_data['elections'][0]
                candidates = Candidate.query.filter_by(election_id=latest.id).all()
                total_votes = Vote.query.filter_by(election_id=latest.id).count()
                results = []
                for candidate in candidates:
                    vote_count = Vote.query.filter_by(candidate_id=candidate.id).count()
                    results.append({
                        'candidate': {'name': candidate.name},
                        'votes': vote_count,
                        'percentage': round((vote_count / total_votes * 100) if total_votes > 0 else 0, 2)
                    })
                results.sort(key=lambda x: x['votes'], reverse=True)
                latest.results = results
            # For all other elections, set results to []
            for election in recent_data['elections'][1:]:
                election.results = []
        except Exception as e:
            logger.error(f"Error fetching recent elections: {str(e)}")
        
        try:
            recent_data['users'] = User.query\
                .filter(User.is_admin == False)\
                .order_by(User.created_at.desc())\
                .limit(5)\
                .all()
        except Exception as e:
            logger.error(f"Error fetching recent users: {str(e)}")
        
        return render_template(
            'admin/dashboard.html',
            stats=stats,
            recent_elections=recent_data['elections'],
            recent_users=recent_data['users']
        )
        
    except Exception as e:
        logger.error(f"Error in admin dashboard: {str(e)}")
        flash("An error occurred while loading the dashboard. Please try again.", "error")
        return render_template(
            'admin/dashboard.html',
            stats={'total_users': 0, 'total_elections': 0, 'active_elections': 0, 'total_votes': 0},
            recent_elections=[],
            recent_users=[]
        )

@bp.route('/elections/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_election():
    if request.method == 'POST':
        try:
            title = request.form['title']
            description = request.form['description']
            
            # Get date and time components
            start_date = request.form['start_date_date']
            start_time = request.form['start_date_time']
            end_date = request.form['end_date_date']
            end_time = request.form['end_date_time']
            
            # Create datetime strings
            start_datetime_str = f"{start_date} {convert_to_24hr(start_time)}"
            end_datetime_str = f"{end_date} {convert_to_24hr(end_time)}"
            
            # Parse datetime strings
            start_datetime = datetime.strptime(start_datetime_str, '%Y-%m-%d %H:%M')
            end_datetime = datetime.strptime(end_datetime_str, '%Y-%m-%d %H:%M')
            
            # Create election object
            election = Election(
                title=title,
                description=description,
                start_date=start_datetime,
                end_date=end_datetime,
                is_active=True
            )
            
            try:
                # Validate dates
                election.validate_dates()
            except ValueError as e:
                flash(str(e), 'error')
                return redirect(url_for('admin.new_election'))
            
            db.session.add(election)
            db.session.commit()
            
            flash(f'Election "{title}" created successfully. Duration: {election.formatted_duration}', 'success')

            sender = current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_USERNAME')
            if not sender:
                logger.warning('Mail credentials are not configured; skipping election announcement emails.')
            else:
                try:
                    users = User.query.filter_by(is_verified=True).all()
                    for user in users:
                        msg = Message(
                            'New Election Announcement',
                            recipients=[user.email],
                            sender=sender,
                            html=render_template(
                                'email/new_election.html',
                                user=user,
                                election=election
                            )
                        )
                        mail.send(msg)
                    # Also send to admin
                    msg_admin = Message(
                        'New Election Announcement',
                        recipients=[sender],
                        sender=sender,
                        html=render_template(
                            'email/new_election.html',
                            user=None,
                            election=election
                        )
                    )
                    mail.send(msg_admin)
                except Exception as e:
                    logger.error(f"Error sending email notifications: {str(e)}")
                    # Continue even if email sending fails
                
            return redirect(url_for('admin.dashboard'))
            
        except Exception as e:
            logger.error(f"Error creating election: {str(e)}")
            flash('An error occurred while creating the election. Please try again.', 'error')
            return redirect(url_for('admin.new_election'))
    
    return render_template('admin/new_election.html')

@bp.route('/elections')
@login_required
@admin_required
def manage_elections():
    elections = Election.query.order_by(Election.created_at.desc()).all()
    return render_template('admin/manage_elections.html', elections=elections)

@bp.route('/election/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_election(id):
    try:
        election = Election.query.get_or_404(id)
        
        if request.method == 'POST':
            try:
                # Get basic info
                election.title = request.form['title']
                election.description = request.form['description']
                
                # Get date and time components
                start_date = request.form['start_date_date']
                start_time = request.form['start_date_time']
                end_date = request.form['end_date_date']
                end_time = request.form['end_date_time']
                
                # Convert time to 24-hour format and create datetime objects
                start_datetime_str = f"{start_date} {convert_to_24hr(start_time)}"
                end_datetime_str = f"{end_date} {convert_to_24hr(end_time)}"
                
                # Parse datetime strings
                start_datetime = datetime.strptime(start_datetime_str, '%Y-%m-%d %H:%M')
                end_datetime = datetime.strptime(end_datetime_str, '%Y-%m-%d %H:%M')
                
                if end_datetime <= start_datetime:
                    flash('End date must be after start date', 'error')
                    return redirect(url_for('admin.edit_election', id=id))
                
                # Update election dates
                election.start_date = start_datetime
                election.end_date = end_datetime
                election.is_active = 'is_active' in request.form
                
                db.session.commit()
                flash('Election updated successfully', 'success')
                return redirect(url_for('admin.manage_elections'))
                
            except ValueError as e:
                logger.error(f"Invalid date/time format in edit election: {str(e)}")
                flash('Invalid date or time format. Please check your input.', 'error')
                return redirect(url_for('admin.edit_election', id=id))
            except Exception as e:
                logger.error(f"Error updating election: {str(e)}")
                flash('An error occurred while updating the election.', 'error')
                return redirect(url_for('admin.edit_election', id=id))
        
        # For GET request, prepare form data
        return render_template('admin/edit_election.html', 
                             election=election,
                             start_date=get_date_string(election.start_date),
                             start_time=convert_to_12hr(election.start_date),
                             end_date=get_date_string(election.end_date),
                             end_time=convert_to_12hr(election.end_date))
                             
    except Exception as e:
        logger.error(f"Error in edit election page: {str(e)}")
        flash('An error occurred while loading the election data.', 'error')
        return redirect(url_for('admin.manage_elections'))

@bp.route('/candidates/new/<int:election_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def new_candidate(election_id):
    election = Election.query.get_or_404(election_id)
    
    if request.method == 'POST':
        name = request.form['name']
        party = request.form['party']
        bio = request.form['bio']
        photo_filename = None
        
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename:
                filename = secure_filename(file.filename)
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'candidates')
                os.makedirs(upload_folder, exist_ok=True)
                file.save(os.path.join(upload_folder, filename))
                photo_filename = filename
        
        candidate = Candidate(
            name=name,
            party=party,
            bio=bio,
            election_id=election_id,
            photo=photo_filename
        )
        db.session.add(candidate)
        db.session.commit()
        
        flash('Candidate added successfully')
        return redirect(url_for('admin.manage_elections'))
    
    return render_template('admin/new_candidate.html', election=election)

@bp.route('/election/<int:election_id>/candidates')
@login_required
@admin_required
def manage_candidates(election_id):
    election = Election.query.get_or_404(election_id)
    candidates = Candidate.query.filter_by(election_id=election_id).all()
    return render_template('admin/manage_candidates.html', election=election, candidates=candidates)

@bp.route('/users')
@login_required
@admin_required
def manage_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/manage_users.html', users=users)

@bp.route('/user/<int:id>/toggle-admin', methods=['POST'])
@login_required
@admin_required
def toggle_admin(id):
    user = User.query.get_or_404(id)
    
    if user == current_user:
        flash('You cannot modify your own admin status')
        return redirect(url_for('admin.manage_users'))
    
    user.is_admin = not user.is_admin
    db.session.commit()
    
    flash(f'Admin status updated for {user.email}')
    return redirect(url_for('admin.manage_users'))

@bp.route('/user/<int:id>/verify', methods=['POST'])
@login_required
@admin_required
def verify_user(id):
    user = User.query.get_or_404(id)
    if not user.is_verified:
        user.is_verified = True
        db.session.commit()
        flash(f"{user.first_name} {user.last_name} has been verified.", "success")
    else:
        flash(f"{user.first_name} {user.last_name} is already verified.", "info")
    return redirect(url_for('admin.manage_users'))

@bp.route('/candidate/<int:id>/verify', methods=['POST'])
@login_required
@admin_required
def verify_candidate(id):
    candidate = Candidate.query.get_or_404(id)
    candidate.verified = True
    db.session.commit()
    flash(f"Candidate {candidate.name} has been verified.", "success")
    return redirect(url_for('admin.manage_candidates', election_id=candidate.election_id))

@bp.route('/election/<int:id>/results')
@login_required
@admin_required
def view_results(id):
    try:
        election = Election.query.get_or_404(id)
        if not election:
            flash('Election not found', 'error')
            return redirect(url_for('admin.dashboard'))
        # Allow admins to view results for both active and ended elections
        candidates = Candidate.query.filter_by(election_id=id).all()
        total_votes = Vote.query.filter_by(election_id=id).count()
        results = []
        for candidate in candidates:
            vote_count = Vote.query.filter_by(candidate_id=candidate.id).count()
            results.append({
                'candidate': candidate,
                'votes': vote_count,
                'percentage': round((vote_count / total_votes * 100) if total_votes > 0 else 0, 2)
            })
        results.sort(key=lambda x: x['votes'], reverse=True)
        return render_template('admin/view_results.html',
                             election=election,
                             results=results,
                             total_votes=total_votes)
    except Exception as e:
        logger.error(f"Error viewing results for election {id}: {str(e)}")
        flash('An error occurred while loading the results', 'error')
        return redirect(url_for('admin.dashboard'))

@bp.route('/election/<int:id>/download-results/<format>')
@login_required
@admin_required
def download_results(id, format='csv'):
    try:
        if format not in ['csv', 'pdf', 'excel']:
            flash('Unsupported download format', 'error')
            return redirect(url_for('admin.view_results', id=id))
            
        if format != 'csv':
            flash(f'{format.upper()} format is not yet supported', 'warning')
            return redirect(url_for('admin.view_results', id=id))
            
        election = Election.query.get_or_404(id)
        candidates = Candidate.query.filter_by(election_id=id).all()
        
        # Create CSV
        si = StringIO()
        writer = csv.writer(si)
        
        # Write headers
        writer.writerow(['Election Results:', election.title])
        writer.writerow(['Generated on:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])
        writer.writerow(['Candidate', 'Party', 'Votes', 'Percentage'])
        
        total_votes = Vote.query.filter_by(election_id=id).count()
        
        # Write results
        for candidate in candidates:
            vote_count = Vote.query.filter_by(candidate_id=candidate.id).count()
            percentage = round((vote_count / total_votes * 100) if total_votes > 0 else 0, 2)
            writer.writerow([
                candidate.name,
                candidate.party,
                vote_count,
                f'{percentage}%'
            ])
            
        writer.writerow([])
        writer.writerow(['Total Votes:', total_votes])
        
        # Create response
        output = si.getvalue()
        si.close()
        
        bio = BytesIO()
        bio.write(output.encode('utf-8'))
        bio.seek(0)
        
        filename = f'election_results_{election.title}_{datetime.now().strftime("%Y%m%d")}.csv'
        return send_file(
            bio,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Error downloading results for election {id}: {str(e)}")
        flash('An error occurred while generating the download', 'error')
        return redirect(url_for('admin.view_results', id=id))

@bp.route('/candidate/<int:candidate_id>/update_photo', methods=['POST'])
@login_required
@admin_required
def update_candidate_photo(candidate_id):
    from werkzeug.utils import secure_filename
    import os
    candidate = Candidate.query.get_or_404(candidate_id)
    if 'photo' not in request.files:
        flash('No file part in the request.', 'danger')
        return redirect(url_for('admin.manage_candidates', election_id=candidate.election_id))
    file = request.files['photo']
    if file.filename == '':
        flash('No selected file.', 'danger')
        return redirect(url_for('admin.manage_candidates', election_id=candidate.election_id))
    if file:
        filename = secure_filename(file.filename)
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'candidates')
        os.makedirs(upload_folder, exist_ok=True)
        file.save(os.path.join(upload_folder, filename))
        candidate.photo = filename
        db.session.commit()
        flash('Candidate photo updated successfully.', 'success')
    else:
        flash('Invalid file.', 'danger')
    return redirect(url_for('admin.manage_candidates', election_id=candidate.election_id))

@bp.route('/queries')
@login_required
@admin_required
def view_queries():
    queries = Query.query.order_by(Query.created_at.desc()).all()
    return render_template('admin/queries.html', queries=queries)

@bp.route('/query/<int:query_id>/respond', methods=['POST'])
@login_required
@admin_required
def respond_query(query_id):
    response = request.form.get('response')
    query = Query.query.get_or_404(query_id)
    query.response = response
    from datetime import datetime
    query.responded_at = datetime.utcnow()
    db.session.commit()
    flash('Response sent to user.', 'success')
    return redirect(url_for('admin.view_queries'))

# Remove/Unregister User Route (must be after bp and admin_required are defined)
@bp.route('/user/<int:id>/remove', methods=['POST'])
@login_required
@admin_required
def remove_user(id):
    user = User.query.get_or_404(id)
    if user == current_user:
        flash('You cannot remove your own account.', 'danger')
        return redirect(url_for('admin.manage_users'))
    try:
        db.session.delete(user)
        db.session.commit()
        flash(f'User {user.email} has been removed.', 'success')
    except Exception as e:
        logger.error(f"Error removing user {user.email}: {str(e)}")
        flash('An error occurred while removing the user.', 'danger')
    return redirect(url_for('admin.manage_users'))