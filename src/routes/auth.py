from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from src.models.database import get_db
from datetime import datetime, timedelta
from bson import ObjectId
import bcrypt
import re

auth_bp = Blueprint('auth', __name__)

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    return True, "Password is valid"

def hash_password(password):
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt)

def check_password(password, hashed):
    """Check password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'email', 'password']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Validate email format
        if not validate_email(data['email']):
            return jsonify({
                'success': False,
                'error': 'Invalid email format'
            }), 400
        
        # Validate password strength
        is_valid, message = validate_password(data['password'])
        if not is_valid:
            return jsonify({
                'success': False,
                'error': message
            }), 400
        
        # Hash password
        hashed_password = hash_password(data['password'])
        
        # Create user object
        user = {
            'name': data['name'].strip(),
            'email': data['email'].lower().strip(),
            'password': hashed_password,
            'user_type': data.get('user_type', 'member'),
            'auth_method': 'local',
            'status': 'active',
            'created_at': datetime.now(),
            'last_login': None,
            'failed_login_attempts': 0,
            'locked_until': None
        }
        
        db = get_db()
        
        # Handle in-memory database
        if hasattr(db, 'users'):
            # Check if email already exists
            if any(u['email'] == user['email'] for u in db.users):
                return jsonify({
                    'success': False,
                    'error': 'Email already registered'
                }), 400
            
            user['_id'] = str(len(db.users) + 1)
            db.users.append(user)
            user_id = user['_id']
        else:
            try:
                result = db.users.insert_one(user)
                user_id = str(result.inserted_id)
            except Exception as e:
                if 'duplicate key' in str(e):
                    return jsonify({
                        'success': False,
                        'error': 'Email already registered'
                    }), 400
                raise
        
        # Create access token
        access_token = create_access_token(
            identity=user_id,
            expires_delta=timedelta(hours=24)
        )
        
        return jsonify({
            'success': True,
            'data': {
                'user_id': user_id,
                'access_token': access_token,
                'user': {
                    'id': user_id,
                    'name': user['name'],
                    'email': user['email'],
                    'user_type': user['user_type']
                }
            }
        }), 201
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('email') or not data.get('password'):
            return jsonify({
                'success': False,
                'error': 'Email and password are required'
            }), 400
        
        email = data['email'].lower().strip()
        password = data['password']
        
        db = get_db()
        
        # Find user
        if hasattr(db, 'users'):
            user = next((u for u in db.users if u['email'] == email), None)
        else:
            user = db.users.find_one({'email': email})
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'Invalid email or password'
            }), 401
        
        # Check if account is locked
        if user.get('locked_until') and user['locked_until'] > datetime.now():
            return jsonify({
                'success': False,
                'error': 'Account temporarily locked due to failed login attempts'
            }), 423
        
        # Check password
        if not check_password(password, user['password']):
            # Increment failed login attempts
            failed_attempts = user.get('failed_login_attempts', 0) + 1
            
            # Lock account after 5 failed attempts
            if failed_attempts >= 5:
                locked_until = datetime.now() + timedelta(minutes=30)
                update_data = {
                    'failed_login_attempts': failed_attempts,
                    'locked_until': locked_until
                }
            else:
                update_data = {'failed_login_attempts': failed_attempts}
            
            # Update user
            if hasattr(db, 'users'):
                user_index = next((i for i, u in enumerate(db.users) if u['email'] == email), None)
                if user_index is not None:
                    for key, value in update_data.items():
                        db.users[user_index][key] = value
            else:
                db.users.update_one(
                    {'email': email},
                    {'$set': update_data}
                )
            
            return jsonify({
                'success': False,
                'error': 'Invalid email or password'
            }), 401
        
        # Reset failed login attempts on successful login
        update_data = {
            'failed_login_attempts': 0,
            'locked_until': None,
            'last_login': datetime.now()
        }
        
        # Update user
        if hasattr(db, 'users'):
            user_index = next((i for i, u in enumerate(db.users) if u['email'] == email), None)
            if user_index is not None:
                for key, value in update_data.items():
                    db.users[user_index][key] = value
        else:
            db.users.update_one(
                {'email': email},
                {'$set': update_data}
            )
        
        # Create access token
        user_id = str(user['_id'])
        access_token = create_access_token(
            identity=user_id,
            expires_delta=timedelta(hours=24)
        )
        
        return jsonify({
            'success': True,
            'data': {
                'access_token': access_token,
                'user': {
                    'id': user_id,
                    'name': user['name'],
                    'email': user['email'],
                    'user_type': user['user_type']
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user profile"""
    try:
        user_id = get_jwt_identity()
        db = get_db()
        
        # Find user
        if hasattr(db, 'users'):
            user = next((u for u in db.users if u['_id'] == user_id), None)
        else:
            user = db.users.find_one({'_id': ObjectId(user_id)})
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Remove sensitive data
        user_data = {
            'id': str(user['_id']),
            'name': user['name'],
            'email': user['email'],
            'user_type': user['user_type'],
            'created_at': user['created_at'],
            'last_login': user.get('last_login')
        }
        
        return jsonify({
            'success': True,
            'data': user_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change user password"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        if not data.get('current_password') or not data.get('new_password'):
            return jsonify({
                'success': False,
                'error': 'Current password and new password are required'
            }), 400
        
        # Validate new password strength
        is_valid, message = validate_password(data['new_password'])
        if not is_valid:
            return jsonify({
                'success': False,
                'error': message
            }), 400
        
        db = get_db()
        
        # Find user
        if hasattr(db, 'users'):
            user = next((u for u in db.users if u['_id'] == user_id), None)
            user_index = next((i for i, u in enumerate(db.users) if u['_id'] == user_id), None)
        else:
            user = db.users.find_one({'_id': ObjectId(user_id)})
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Check current password
        if not check_password(data['current_password'], user['password']):
            return jsonify({
                'success': False,
                'error': 'Current password is incorrect'
            }), 401
        
        # Hash new password
        new_hashed_password = hash_password(data['new_password'])
        
        # Update password
        if hasattr(db, 'users'):
            db.users[user_index]['password'] = new_hashed_password
        else:
            db.users.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': {'password': new_hashed_password}}
            )
        
        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

