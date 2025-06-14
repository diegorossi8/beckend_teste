from flask import Blueprint, request, jsonify
from src.models.database import get_db
from datetime import datetime
from bson import ObjectId

testimonials_bp = Blueprint('testimonials', __name__)

@testimonials_bp.route('/', methods=['GET'])
def get_testimonials():
    """Get all testimonials"""
    try:
        db = get_db()
        
        # Handle in-memory database
        if hasattr(db, 'testimonials'):
            testimonials = db.testimonials
        else:
            testimonials = list(db.testimonials.find())
        
        # Convert ObjectId to string for JSON serialization
        for testimonial in testimonials:
            if '_id' in testimonial and isinstance(testimonial['_id'], ObjectId):
                testimonial['_id'] = str(testimonial['_id'])
        
        return jsonify({
            'success': True,
            'data': testimonials
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@testimonials_bp.route('/', methods=['POST'])
def create_testimonial():
    """Create a new testimonial"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['client_name', 'company', 'position', 'text', 'rating']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Create testimonial object
        testimonial = {
            'client_name': data['client_name'],
            'company': data['company'],
            'position': data['position'],
            'text': data['text'],
            'rating': int(data['rating']),
            'status': data.get('status', 'active'),
            'created_at': datetime.now()
        }
        
        db = get_db()
        
        # Handle in-memory database
        if hasattr(db, 'testimonials'):
            testimonial['_id'] = str(len(db.testimonials) + 1)
            db.testimonials.append(testimonial)
            testimonial_id = testimonial['_id']
        else:
            result = db.testimonials.insert_one(testimonial)
            testimonial_id = str(result.inserted_id)
        
        return jsonify({
            'success': True,
            'data': {'_id': testimonial_id}
        }), 201
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@testimonials_bp.route('/<testimonial_id>', methods=['PUT'])
def update_testimonial(testimonial_id):
    """Update a testimonial"""
    try:
        data = request.get_json()
        
        db = get_db()
        
        # Handle in-memory database
        if hasattr(db, 'testimonials'):
            testimonial_index = next((i for i, t in enumerate(db.testimonials) if t['_id'] == testimonial_id), None)
            if testimonial_index is None:
                return jsonify({
                    'success': False,
                    'error': 'Testimonial not found'
                }), 404
            
            # Update testimonial
            for key, value in data.items():
                if key != '_id':
                    db.testimonials[testimonial_index][key] = value
            
            modified_count = 1
        else:
            result = db.testimonials.update_one(
                {'_id': ObjectId(testimonial_id)},
                {'$set': data}
            )
            modified_count = result.modified_count
        
        if modified_count == 0:
            return jsonify({
                'success': False,
                'error': 'Testimonial not found'
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'Testimonial updated successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@testimonials_bp.route('/<testimonial_id>', methods=['DELETE'])
def delete_testimonial(testimonial_id):
    """Delete a testimonial"""
    try:
        db = get_db()
        
        # Handle in-memory database
        if hasattr(db, 'testimonials'):
            testimonial_index = next((i for i, t in enumerate(db.testimonials) if t['_id'] == testimonial_id), None)
            if testimonial_index is None:
                return jsonify({
                    'success': False,
                    'error': 'Testimonial not found'
                }), 404
            
            db.testimonials.pop(testimonial_index)
            deleted_count = 1
        else:
            result = db.testimonials.delete_one({'_id': ObjectId(testimonial_id)})
            deleted_count = result.deleted_count
        
        if deleted_count == 0:
            return jsonify({
                'success': False,
                'error': 'Testimonial not found'
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'Testimonial deleted successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

