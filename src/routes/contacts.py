from flask import Blueprint, request, jsonify
from src.models.database import get_db
from datetime import datetime
from bson import ObjectId

contacts_bp = Blueprint('contacts', __name__)

@contacts_bp.route('/', methods=['GET'])
def get_contacts():
    """Get all contacts"""
    try:
        db = get_db()
        
        # Handle in-memory database
        if hasattr(db, 'contacts'):
            contacts = db.contacts
        else:
            contacts = list(db.contacts.find().sort('created_at', -1))
        
        # Convert ObjectId to string for JSON serialization
        for contact in contacts:
            if '_id' in contact and isinstance(contact['_id'], ObjectId):
                contact['_id'] = str(contact['_id'])
        
        return jsonify({
            'success': True,
            'data': contacts
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@contacts_bp.route('/', methods=['POST'])
def create_contact():
    """Create a new contact message"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'email', 'message']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Create contact object
        contact = {
            'name': data['name'],
            'email': data['email'],
            'company': data.get('company', ''),
            'message': data['message'],
            'status': 'new',
            'created_at': datetime.now()
        }
        
        db = get_db()
        
        # Handle in-memory database
        if hasattr(db, 'contacts'):
            contact['_id'] = str(len(db.contacts) + 1)
            db.contacts.append(contact)
            contact_id = contact['_id']
        else:
            result = db.contacts.insert_one(contact)
            contact_id = str(result.inserted_id)
        
        return jsonify({
            'success': True,
            'data': {'_id': contact_id}
        }), 201
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@contacts_bp.route('/<contact_id>', methods=['PUT'])
def update_contact(contact_id):
    """Update a contact (e.g., mark as responded)"""
    try:
        data = request.get_json()
        
        db = get_db()
        
        # Handle in-memory database
        if hasattr(db, 'contacts'):
            contact_index = next((i for i, c in enumerate(db.contacts) if c['_id'] == contact_id), None)
            if contact_index is None:
                return jsonify({
                    'success': False,
                    'error': 'Contact not found'
                }), 404
            
            # Update contact
            for key, value in data.items():
                if key != '_id':
                    db.contacts[contact_index][key] = value
            
            modified_count = 1
        else:
            result = db.contacts.update_one(
                {'_id': ObjectId(contact_id)},
                {'$set': data}
            )
            modified_count = result.modified_count
        
        if modified_count == 0:
            return jsonify({
                'success': False,
                'error': 'Contact not found'
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'Contact updated successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@contacts_bp.route('/<contact_id>', methods=['DELETE'])
def delete_contact(contact_id):
    """Delete a contact"""
    try:
        db = get_db()
        
        # Handle in-memory database
        if hasattr(db, 'contacts'):
            contact_index = next((i for i, c in enumerate(db.contacts) if c['_id'] == contact_id), None)
            if contact_index is None:
                return jsonify({
                    'success': False,
                    'error': 'Contact not found'
                }), 404
            
            db.contacts.pop(contact_index)
            deleted_count = 1
        else:
            result = db.contacts.delete_one({'_id': ObjectId(contact_id)})
            deleted_count = result.deleted_count
        
        if deleted_count == 0:
            return jsonify({
                'success': False,
                'error': 'Contact not found'
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'Contact deleted successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

