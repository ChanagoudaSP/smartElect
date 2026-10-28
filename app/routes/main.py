from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file, current_app
from flask_login import login_required, current_user
from app.utils.encryption import Encryption
from app.utils.time_utils import convert_to_12hr
from app import db
from datetime import datetime
import logging
import io
import csv
from app.models.models import Election, Candidate, Vote, User
from app.models.query import Query
from flask import current_app
from sqlalchemy import case, func

bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

@bp.app_template_filter('format_time')
def format_time(datetime_obj):
    """Format time in 12-hour format"""
    return convert_to_12hr(datetime_obj) if datetime_obj else ''

@bp.route('/')
def index():
    """Home page route"""
    try:
        from app.utils.db_utils import get_active_elections, get_upcoming_elections
        now_local = datetime.now()
        active_elections = get_active_elections()
        upcoming_elections = get_upcoming_elections()
        all_elections = Election.query.order_by(Election.end_date.desc()).all()
        past_elections = [e for e in all_elections if not e.is_active or now_local >= e.end_date]
        # Handle admin redirect
        if current_user.is_authenticated and current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        template = 'main/elections.html' if current_user.is_authenticated else 'main/index.html'
        return render_template(template, 
                             elections=active_elections,
                             upcoming_elections=upcoming_elections,
                             past_elections=past_elections,
                             now=now_local)
                             
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        flash("An error occurred while loading the page. Please try again.", "error")
        return render_template('main/index.html', 
                             elections=[],
                             now=datetime.utcnow())

@bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard route"""
    try:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        from app.utils.db_utils import get_active_elections, get_upcoming_elections
        now = datetime.utcnow()
        total_elections = Election.query.count()
        active_elections = get_active_elections()
        upcoming_elections = get_upcoming_elections()
        all_elections = Election.query.order_by(Election.end_date.desc()).all()
        # Past elections: not active or already ended
        past_elections = [e for e in all_elections if not e.is_active or now >= e.end_date]
        user_votes = Vote.query.filter_by(user_id=current_user.id).count()
        return render_template('main/dashboard.html',
                             total_elections=total_elections,
                             elections_voted=user_votes,
                             active_elections_count=len(active_elections),
                             active_elections=active_elections,
                             upcoming_elections=upcoming_elections,
                             past_elections=past_elections,
                             now=now)
    except Exception as e:
        logger.error(f"Error in dashboard route: {str(e)}")
        flash("An error occurred while loading the dashboard. Please try again.", "error")
        return redirect(url_for('main.index'))

@bp.route('/elections')
@login_required
def elections():
    """View all elections"""
    try:
        from app.utils.db_utils import get_active_elections, get_upcoming_elections
        now_local = datetime.now()
        active_elections = get_active_elections()
        upcoming_elections = get_upcoming_elections()
        # Get all elections for past_elections logic
        all_elections = Election.query.order_by(Election.end_date.desc()).all()
        past_elections = [e for e in all_elections if not e.is_active or now_local >= e.end_date]
        return render_template('main/elections.html',
                             elections=active_elections,
                             upcoming_elections=upcoming_elections,
                             past_elections=past_elections,
                             now=now_local)
                             
    except Exception as e:
        logger.error(f"Error in elections route: {str(e)}")
        flash("An error occurred while loading the elections. Please try again.", "error")
        return render_template('main/elections.html',
                             elections=[],
                             past_elections=[],
                             now=datetime.utcnow())

@bp.route('/help')
def knowledge_base():
    """Help Center / Knowledge Base route"""
    try:
        return render_template('main/help.html')
    except Exception as e:
        logger.error(f"Error in help center route: {str(e)}")
        flash("An error occurred while loading the help center. Please try again.", "error")
        return render_template('main/help.html')

@bp.route('/election/<int:id>')
@login_required
def election_detail(id):
    """Election detail route"""
    try:
        now = datetime.utcnow()
        election = db.session.query(Election).get_or_404(id)
        
        # Preload relationships to avoid N+1 queries
        candidates = Candidate.query.filter_by(election_id=id).all()
        
        # Use model methods for voting logic
        can_vote = election.can_vote(current_user)
        has_voted = election.user_has_voted(current_user)
        your_vote = None
        status_message = None
        status_type = "info"

        if has_voted:
            # Find the candidate the user voted for
            existing_vote = Vote.query.filter_by(user_id=current_user.id, election_id=id).first()
            your_vote = next((c for c in candidates if c.id == existing_vote.candidate_id), None) if existing_vote else None
            if your_vote:
                status_message = f"You have voted for {your_vote.name} ({your_vote.party})"
            else:
                status_message = "You have already voted in this election."
            status_type = "success"
        elif not current_user.is_verified:
            status_message = "You must be verified to vote in this election"
            status_type = "warning"
        elif not election.is_active:
            status_message = "This election is not currently active"
            status_type = "danger"
        elif election.has_ended:
            status_message = "This election has ended"
            status_type = "secondary"
        elif not election.has_started:
            time_to_start = (election.start_date - now).total_seconds()
            minutes_to_start = int(time_to_start / 60)
            if minutes_to_start <= 30:
                status_message = f"Election starts in {minutes_to_start} minutes"
            else:
                status_message = f"Election starts {election.start_date.strftime('%B %d, %Y at %I:%M %p')}"
            status_type = "info"
        else:
            status_message = "Election is in progress - you can now vote"
            status_type = "success"

        # Get total votes with proper error handling
        total_votes = None
        if election.has_ended or current_user.is_admin:
            try:
                total_votes = db.session.query(db.func.count(Vote.id)).filter_by(election_id=id).scalar()
            except Exception as e:
                logger.error(f"Error counting votes: {str(e)}")
                total_votes = 0

        return render_template('main/election_detail.html',
                            election=election,
                            candidates=candidates,
                            can_vote=can_vote,
                            has_voted=has_voted,
                            your_vote=your_vote,
                            status_message=status_message,
                            status_type=status_type,
                            total_votes=total_votes,
                            now=now)

    except Exception as e:
        logger.error(f"Error in election_detail route: {str(e)}")
        flash("An error occurred while loading the election details. Please try again.", "error")
        # Add more context to the error message if possible
        if "no such table" in str(e).lower():
            flash("Database setup issue. Please contact administrator.", "error")
        elif "not found" in str(e).lower():
            flash("The requested election was not found.", "error")
        return redirect(url_for('main.elections'))

@bp.route('/election/<int:id>/results')
@login_required
def view_results(id):
    """View election results route for users"""
    try:
        # Get election or return 404
        election = Election.query.get_or_404(id)
        now = datetime.utcnow()
        
        # Only allow viewing results if election has ended
        if election.end_date > now and not current_user.is_admin:
            flash('Results will be available after the election ends.', 'warning')
            return redirect(url_for('main.election_detail', id=id))
        
        # Get candidates and votes with proper error handling
        try:
            candidates = Candidate.query.filter_by(election_id=id).all()
            total_votes = Vote.query.filter_by(election_id=id).count()
        except Exception as e:
            logger.error(f"Database error while fetching election results: {str(e)}")
            flash("An error occurred while loading the results. Please try again.", "error")
            return redirect(url_for('main.election_detail', id=id))
        
        # Calculate results safely
        results = []
        for candidate in candidates:
            try:
                vote_count = Vote.query.filter_by(
                    election_id=id,
                    candidate_id=candidate.id
                ).count()
                
                # Calculate percentage safely
                percentage = 0
                if total_votes > 0:
                    percentage = round((vote_count / total_votes) * 100, 2)
                
                results.append({
                    'candidate': candidate,
                    'votes': vote_count,
                    'percentage': percentage
                })
            except Exception as e:
                logger.error(f"Error calculating results for candidate {candidate.id}: {str(e)}")
                continue
        
        # Sort results by votes (descending)
        results.sort(key=lambda x: x['votes'], reverse=True)
        
        return render_template('main/view_results.html',
                             election=election,
                             results=results,
                             total_votes=total_votes)
                             
    except Exception as e:
        logger.error(f"Error in view_results route: {str(e)}")
        flash("An error occurred while loading the results. Please try again.", "error")
        return redirect(url_for('main.elections'))

@bp.route('/vote/<int:election_id>/<int:candidate_id>', methods=['POST'])
@login_required
def cast_vote(election_id, candidate_id):
    """Cast a vote with improved transaction handling"""
    logger.info(f"Vote attempt - election:{election_id} candidate:{candidate_id}")
    
    try:
        # First validate the candidate exists
        candidate = Candidate.query.filter_by(id=candidate_id, election_id=election_id).first()
        if not candidate:
            flash("Invalid candidate selection.", "error")
            return redirect(url_for('main.election_detail', id=election_id))

        # Start transaction
        with db.session.begin_nested():
            # Lock the election record to prevent race conditions
            election = db.session.query(Election).with_for_update().get_or_404(election_id)
            
            # Comprehensive validation
            now = datetime.utcnow()
            
            if not election.is_active:
                raise ValueError("This election is not active")
                
            if now < election.start_date:
                raise ValueError("This election has not started yet")
                
            if now >= election.end_date:
                raise ValueError("This election has ended")
                
            if not current_user.is_verified:
                raise ValueError("You must be verified to vote in this election")
                
            # Check for existing vote with lock
            existing_vote = db.session.query(Vote).with_for_update().filter_by(
                user_id=current_user.id,
                election_id=election_id
            ).first()
            
            if existing_vote:
                raise ValueError("You have already voted in this election")
                
            # Create vote with encryption
            from app.utils.encryption import Encryption
            encryption = Encryption()
            encrypted_data = encryption.encrypt(str(candidate_id))
            
            vote = Vote(
                user_id=current_user.id,
                election_id=election_id,
                candidate_id=candidate_id,
                encrypted_vote=encrypted_data
            )
            db.session.add(vote)
            
        # Commit the transaction
        db.session.commit()
        logger.info(f"Vote recorded successfully - election:{election_id} user:{current_user.id}")
        flash("Your vote has been recorded successfully!", "success")
        
    except ValueError as e:
        db.session.rollback()
        logger.warning(f"Vote failed - election:{election_id} user:{current_user.id} - {str(e)}")
        flash(str(e), "error")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Vote error - election:{election_id} user:{current_user.id} - {str(e)}")
        flash(f"An error occurred while recording your vote: {str(e)}", "error")
    
    return redirect(url_for('main.election_detail', id=election_id))

@bp.route('/results/<int:election_id>')
def election_results(election_id):
    try:
        election = Election.query.get_or_404(election_id)
        # Only show results if election has ended
        if election.end_date > datetime.utcnow():
            flash('Results will be available after the election ends')
            return redirect(url_for('main.election_detail', id=election_id))
        candidates = Candidate.query.filter_by(election_id=election_id).all()
        results = []
        total_votes = Vote.query.filter_by(election_id=election_id).count()
        for candidate in candidates:
            votes = Vote.query.filter_by(
                election_id=election_id,
                candidate_id=candidate.id
            ).count()
            percentage = (votes / total_votes * 100) if total_votes > 0 else 0
            results.append({
                'candidate': candidate,
                'votes': votes,
                'percentage': round(percentage, 2)
            })
        from datetime import datetime as dt
        return render_template('main/results.html',
                             election=election,
                             results=results,
                             total_votes=total_votes,
                             now=dt.utcnow())
    except Exception as e:
        logger.error(f"Error loading results for election {election_id}: {str(e)}")
        flash(f"An error occurred while loading the results: {str(e)}", "error")
        return redirect(url_for('main.election_detail', id=election_id))

@bp.route('/election/<int:election_id>/download/<format>')
@login_required
def download_results(election_id, format):
    election = Election.query.get_or_404(election_id)
    
    # Only allow downloading results if election has ended
    if election.end_date > datetime.utcnow():
        flash('Results will be available after the election ends')
        return redirect(url_for('main.election_detail', id=election_id))
    
    candidates = Candidate.query.filter_by(election_id=election_id).all()
    total_votes = Vote.query.filter_by(election_id=election_id).count()
    
    results = []
    for candidate in candidates:
        votes = Vote.query.filter_by(
            election_id=election_id,
            candidate_id=candidate.id
        ).count()
        percentage = (votes / total_votes * 100) if total_votes > 0 else 0
        results.append({
            'name': candidate.name,
            'party': candidate.party,
            'votes': votes,
            'percentage': round(percentage, 2)
        })
    
    if format == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow(['Election Results:', election.title])
        writer.writerow(['Generated on:', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])
        writer.writerow(['Candidate', 'Party', 'Votes', 'Percentage'])
        
        # Write results
        for result in results:
            writer.writerow([
                result['name'],
                result['party'],
                result['votes'],
                f"{result['percentage']}%"
            ])
        
        # Write total
        writer.writerow([])
        writer.writerow(['Total Votes:', total_votes])
        
        # Create the response
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'election_results_{election.title}_{datetime.utcnow().strftime("%Y%m%d")}.csv'
        )
    
    elif format == 'excel':
        try:
            import pandas as pd
            
            # Create DataFrame
            df = pd.DataFrame(results)
            
            # Create Excel writer
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Results', index=False)
                
                # Get workbook and worksheet
                workbook = writer.book
                worksheet = writer.sheets['Results']
                
                # Add formatting
                header_format = workbook.add_format({
                    'bold': True,
                    'bg_color': '#0066cc',
                    'font_color': 'white'
                })
                
                # Format header row
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                # Adjust column widths
                worksheet.set_column('A:D', 15)
            
            output.seek(0)
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'election_results_{election.title}_{datetime.utcnow().strftime("%Y%m%d")}.xlsx'
            )
            
        except ImportError:
            flash('Excel export is not available. Please try CSV format.')
            return redirect(url_for('main.dashboard'))
    
    else:
        flash('Unsupported format. Please choose CSV or Excel.')
        return redirect(url_for('main.dashboard'))

@bp.route('/submit-query', methods=['POST'])
@login_required
def submit_query():
    message = request.form.get('message')
    if not message or not message.strip():
        flash('Please enter a valid question or query.', 'warning')
        return redirect(url_for('main.knowledge_base'))
    try:
        query = Query(user_id=current_user.id, message=message.strip())
        db.session.add(query)
        db.session.commit()
        flash('Your question/query has been submitted. The admin will respond soon.', 'success')
    except Exception as e:
        current_app.logger.error(f"Error saving voter query: {e}")
        flash('An error occurred while submitting your query.', 'danger')
    return redirect(url_for('main.knowledge_base'))

@bp.route('/profile')
@login_required
def profile():
    return render_template('main/profile.html', user=current_user)