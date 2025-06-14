from flask import Blueprint, request, jsonify
from src.models.database import get_db
from datetime import datetime
from bson import ObjectId

users_bp = Blueprint('users', __name__)

@users_bp.route('/', methods=['GET'])
def get_users():
    """Get all users"""
    try:
        db = get_db()
        
        # Handle in-memory database
        if hasattr(db, 'users'):
            users = db.users
        else:
            users = list(db.users.find())
        
        # Convert ObjectId to string and remove sensitive data
        for user in users:
            if '_id' in user and isinstance(user['_id'], ObjectId):
                user['_id'] = str(user['_id'])
            # Remove sensitive fields
            user.pop('password', None)
        
        return jsonify({
            'success': True,
            'data': users
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@users_bp.route('/', methods=['POST'])
def create_user():
    """Create a new user"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'email']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Create user object
        user = {
            'name': data['name'],
            'email': data['email'],
            'user_type': data.get('user_type', 'member'),  # member, admin, premium
            'auth_method': data.get('auth_method', 'auth0'),
            'status': 'active',
            'created_at': datetime.now(),
            'last_login': None
        }
        
        db = get_db()
        
        # Handle in-memory database
        if hasattr(db, 'users'):
            # Check if email already exists
            if any(u['email'] == user['email'] for u in db.users):
                return jsonify({
                    'success': False,
                    'error': 'Email already exists'
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
                        'error': 'Email already exists'
                    }), 400
                raise
        
        return jsonify({
            'success': True,
            'data': {'_id': user_id}
        }), 201
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@users_bp.route('/<user_id>', methods=['PUT'])
def update_user(user_id):
    """Update a user"""
    try:
        data = request.get_json()
        
        # Remove sensitive fields that shouldn't be updated via this endpoint
        data.pop('password', None)
        data.pop('_id', None)
        
        db = get_db()
        
        # Handle in-memory database
        if hasattr(db, 'users'):
            user_index = next((i for i, u in enumerate(db.users) if u['_id'] == user_id), None)
            if user_index is None:
                return jsonify({
                    'success': False,
                    'error': 'User not found'
                }), 404
            
            # Update user
            for key, value in data.items():
                db.users[user_index][key] = value
            
            modified_count = 1
        else:
            result = db.users.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': data}
            )
            modified_count = result.modified_count
        
        if modified_count == 0:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'User updated successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@users_bp.route('/<user_id>/login', methods=['POST'])
def update_last_login(user_id):
    """Update user's last login timestamp"""
    try:
        db = get_db()
        
        # Handle in-memory database
        if hasattr(db, 'users'):
            user_index = next((i for i, u in enumerate(db.users) if u['_id'] == user_id), None)
            if user_index is None:
                return jsonify({
                    'success': False,
                    'error': 'User not found'
                }), 404
            
            db.users[user_index]['last_login'] = datetime.now()
            modified_count = 1
        else:
            result = db.users.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': {'last_login': datetime.now()}}
            )
            modified_count = result.modified_count
        
        if modified_count == 0:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'Last login updated successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

