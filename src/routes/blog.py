from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.database import get_db
from datetime import datetime
from bson import ObjectId
import html
import re

# Input validation and sanitization
def sanitize_input(text):
    """Sanitize user input to prevent XSS"""
    if not isinstance(text, str):
        return text
    # HTML escape
    text = html.escape(text)
    # Remove potentially dangerous characters
    text = re.sub(r'[<>"\']', '', text)
    return text.strip()

def validate_blog_post_data(data):
    """Validate blog post data"""
    errors = []
    
    if not data.get('title') or len(data['title'].strip()) < 3:
        errors.append('Title must be at least 3 characters long')
    
    if not data.get('content') or len(data['content'].strip()) < 10:
        errors.append('Content must be at least 10 characters long')
    
    if not data.get('category') or data['category'] not in ['Tutorial', 'Artigo', 'Estudo de Caso']:
        errors.append('Category must be one of: Tutorial, Artigo, Estudo de Caso')
    
    if not data.get('author') or len(data['author'].strip()) < 2:
        errors.append('Author must be at least 2 characters long')
    
    return errors

# Protected blog routes
blog_bp = Blueprint('blog', __name__)

@blog_bp.route('/posts', methods=['GET'])
def get_posts():
    """Get all blog posts (public endpoint)"""
    try:
        db = get_db()
        
        # Handle in-memory database
        if hasattr(db, 'blog_posts'):
            posts = [post for post in db.blog_posts if post.get('status') == 'published']
        else:
            posts = list(db.blog_posts.find({'status': 'published'}))
        
        # Convert ObjectId to string for JSON serialization
        for post in posts:
            if '_id' in post and isinstance(post['_id'], ObjectId):
                post['_id'] = str(post['_id'])
        
        return jsonify({
            'success': True,
            'data': posts
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@blog_bp.route('/posts/admin', methods=['GET'])
@jwt_required()
def get_all_posts():
    """Get all blog posts including drafts (admin only)"""
    try:
        user_id = get_jwt_identity()
        db = get_db()
        
        # Check if user is admin
        if hasattr(db, 'users'):
            user = next((u for u in db.users if u['_id'] == user_id), None)
        else:
            user = db.users.find_one({'_id': ObjectId(user_id)})
        
        if not user or user.get('user_type') != 'admin':
            return jsonify({
                'success': False,
                'error': 'Admin access required'
            }), 403
        
        # Handle in-memory database
        if hasattr(db, 'blog_posts'):
            posts = db.blog_posts
        else:
            posts = list(db.blog_posts.find())
        
        # Convert ObjectId to string for JSON serialization
        for post in posts:
            if '_id' in post and isinstance(post['_id'], ObjectId):
                post['_id'] = str(post['_id'])
        
        return jsonify({
            'success': True,
            'data': posts
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@blog_bp.route('/posts/<post_id>', methods=['GET'])
def get_post(post_id):
    """Get a specific blog post"""
    try:
        # Validate post_id format
        if not post_id or len(post_id) > 50:
            return jsonify({
                'success': False,
                'error': 'Invalid post ID'
            }), 400
        
        db = get_db()
        
        # Handle in-memory database
        if hasattr(db, 'blog_posts'):
            post = next((p for p in db.blog_posts if p['_id'] == post_id), None)
        else:
            try:
                post = db.blog_posts.find_one({'_id': ObjectId(post_id)})
                if post:
                    post['_id'] = str(post['_id'])
            except:
                return jsonify({
                    'success': False,
                    'error': 'Invalid post ID format'
                }), 400
        
        if not post:
            return jsonify({
                'success': False,
                'error': 'Post not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': post
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@blog_bp.route('/posts', methods=['POST'])
@jwt_required()
def create_post():
    """Create a new blog post (admin only)"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        db = get_db()
        
        # Check if user is admin
        if hasattr(db, 'users'):
            user = next((u for u in db.users if u['_id'] == user_id), None)
        else:
            user = db.users.find_one({'_id': ObjectId(user_id)})
        
        if not user or user.get('user_type') != 'admin':
            return jsonify({
                'success': False,
                'error': 'Admin access required'
            }), 403
        
        # Validate input data
        errors = validate_blog_post_data(data)
        if errors:
            return jsonify({
                'success': False,
                'error': '; '.join(errors)
            }), 400
        
        # Sanitize input
        post = {
            'title': sanitize_input(data['title']),
            'content': sanitize_input(data['content']),
            'category': sanitize_input(data['category']),
            'author': sanitize_input(data['author']),
            'status': sanitize_input(data.get('status', 'draft')),
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        # Handle in-memory database
        if hasattr(db, 'blog_posts'):
            post['_id'] = str(len(db.blog_posts) + 1)
            db.blog_posts.append(post)
            post_id = post['_id']
        else:
            result = db.blog_posts.insert_one(post)
            post_id = str(result.inserted_id)
        
        return jsonify({
            'success': True,
            'data': {'_id': post_id}
        }), 201
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@blog_bp.route('/posts/<post_id>', methods=['PUT'])
@jwt_required()
def update_post(post_id):
    """Update a blog post (admin only)"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validate post_id format
        if not post_id or len(post_id) > 50:
            return jsonify({
                'success': False,
                'error': 'Invalid post ID'
            }), 400
        
        db = get_db()
        
        # Check if user is admin
        if hasattr(db, 'users'):
            user = next((u for u in db.users if u['_id'] == user_id), None)
        else:
            user = db.users.find_one({'_id': ObjectId(user_id)})
        
        if not user or user.get('user_type') != 'admin':
            return jsonify({
                'success': False,
                'error': 'Admin access required'
            }), 403
        
        # Sanitize input data
        sanitized_data = {}
        for key, value in data.items():
            if key != '_id':
                sanitized_data[key] = sanitize_input(value) if isinstance(value, str) else value
        
        sanitized_data['updated_at'] = datetime.now()
        
        # Handle in-memory database
        if hasattr(db, 'blog_posts'):
            post_index = next((i for i, p in enumerate(db.blog_posts) if p['_id'] == post_id), None)
            if post_index is None:
                return jsonify({
                    'success': False,
                    'error': 'Post not found'
                }), 404
            
            # Update post
            for key, value in sanitized_data.items():
                db.blog_posts[post_index][key] = value
            
            modified_count = 1
        else:
            try:
                result = db.blog_posts.update_one(
                    {'_id': ObjectId(post_id)},
                    {'$set': sanitized_data}
                )
                modified_count = result.modified_count
            except:
                return jsonify({
                    'success': False,
                    'error': 'Invalid post ID format'
                }), 400
        
        if modified_count == 0:
            return jsonify({
                'success': False,
                'error': 'Post not found'
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'Post updated successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@blog_bp.route('/posts/<post_id>', methods=['DELETE'])
@jwt_required()
def delete_post(post_id):
    """Delete a blog post (admin only)"""
    try:
        user_id = get_jwt_identity()
        
        # Validate post_id format
        if not post_id or len(post_id) > 50:
            return jsonify({
                'success': False,
                'error': 'Invalid post ID'
            }), 400
        
        db = get_db()
        
        # Check if user is admin
        if hasattr(db, 'users'):
            user = next((u for u in db.users if u['_id'] == user_id), None)
        else:
            user = db.users.find_one({'_id': ObjectId(user_id)})
        
        if not user or user.get('user_type') != 'admin':
            return jsonify({
                'success': False,
                'error': 'Admin access required'
            }), 403
        
        # Handle in-memory database
        if hasattr(db, 'blog_posts'):
            post_index = next((i for i, p in enumerate(db.blog_posts) if p['_id'] == post_id), None)
            if post_index is None:
                return jsonify({
                    'success': False,
                    'error': 'Post not found'
                }), 404
            
            db.blog_posts.pop(post_index)
            deleted_count = 1
        else:
            try:
                result = db.blog_posts.delete_one({'_id': ObjectId(post_id)})
                deleted_count = result.deleted_count
            except:
                return jsonify({
                    'success': False,
                    'error': 'Invalid post ID format'
                }), 400
        
        if deleted_count == 0:
            return jsonify({
                'success': False,
                'error': 'Post not found'
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'Post deleted successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

