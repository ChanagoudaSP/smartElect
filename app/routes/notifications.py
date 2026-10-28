from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.models.notification import Notification
from app import db

bp = Blueprint('notifications', __name__)

@bp.route('/notifications')
@login_required
def get_notifications():
    try:
        notifications = Notification.query.filter_by(user_id=current_user.id)\
            .order_by(Notification.created_at.desc())\
            .limit(10)\
            .all()
        return jsonify([n.to_dict() for n in notifications])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/notifications/mark-read', methods=['POST'])
@login_required
def mark_notification_read():
    try:
        data = request.get_json()
        if not data or 'notification_id' not in data:
            return jsonify({'error': 'Notification ID is required'}), 400
            
        notification = Notification.query.filter_by(
            id=data['notification_id'],
            user_id=current_user.id
        ).first()
        
        if not notification:
            return jsonify({'error': 'Notification not found'}), 404
        
        notification.is_read = True
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    try:
        Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).update({'is_read': True})
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500