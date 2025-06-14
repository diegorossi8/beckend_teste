from pymongo import MongoClient
from datetime import datetime
import os

# MongoDB connection
client = None
db = None

def init_db():
    global client, db
    # Use MongoDB Atlas connection string from environment variable
    mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    
    try:
        client = MongoClient(mongo_uri)
        db = client['ai_consulting']
        
        # Test connection
        client.admin.command('ping')
        print("MongoDB connected successfully")
        
        # Create collections if they don't exist
        create_collections()
        
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        # Fallback to in-memory storage for development
        db = InMemoryDB()

def create_collections():
    """Create collections and indexes"""
    if db is None:
        return
        
    # Blog posts collection
    if 'blog_posts' not in db.list_collection_names():
        db.create_collection('blog_posts')
        db.blog_posts.create_index([('title', 1)])
        db.blog_posts.create_index([('category', 1)])
        db.blog_posts.create_index([('created_at', -1)])
    
    # Testimonials collection
    if 'testimonials' not in db.list_collection_names():
        db.create_collection('testimonials')
        db.testimonials.create_index([('client_name', 1)])
        db.testimonials.create_index([('status', 1)])
    
    # Contacts collection
    if 'contacts' not in db.list_collection_names():
        db.create_collection('contacts')
        db.contacts.create_index([('email', 1)])
        db.contacts.create_index([('created_at', -1)])
    
    # Users collection
    if 'users' not in db.list_collection_names():
        db.create_collection('users')
        db.users.create_index([('email', 1)], unique=True)

def get_db():
    """Get database instance"""
    return db

class InMemoryDB:
    """Fallback in-memory database for development"""
    def __init__(self):
        self.blog_posts = []
        self.testimonials = []
        self.contacts = []
        self.users = []
        self._init_sample_data()
    
    def _init_sample_data(self):
        """Initialize with sample data"""
        # Sample blog posts
        self.blog_posts = [
            {
                '_id': '1',
                'title': 'Como implementar ChatGPT na sua empresa',
                'content': 'A implementação de IA generativa como o ChatGPT pode revolucionar a forma como sua empresa opera...',
                'category': 'Tutorial',
                'author': 'Dr. Ana Silva',
                'status': 'published',
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            },
            {
                '_id': '2',
                'title': 'ROI de projetos de IA: Como medir o sucesso',
                'content': 'Medir o retorno sobre investimento em projetos de IA é crucial para justificar os gastos...',
                'category': 'Artigo',
                'author': 'Prof. Carlos Santos',
                'status': 'draft',
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
        ]
        
        # Sample testimonials
        self.testimonials = [
            {
                '_id': '1',
                'client_name': 'João Silva',
                'company': 'TechCorp',
                'position': 'CEO',
                'text': 'A implementação da IA revolucionou nosso atendimento ao cliente. Reduzimos o tempo de resposta em 80% e aumentamos a satisfação significativamente.',
                'rating': 5,
                'status': 'active',
                'created_at': datetime.now()
            },
            {
                '_id': '2',
                'client_name': 'Maria Oliveira',
                'company': 'InnovaCorp',
                'position': 'Diretora',
                'text': 'O ROI foi impressionante. Em 6 meses, já tínhamos recuperado todo o investimento e continuamos vendo resultados exponenciais.',
                'rating': 5,
                'status': 'active',
                'created_at': datetime.now()
            }
        ]
        
        # Sample contacts
        self.contacts = [
            {
                '_id': '1',
                'name': 'Carlos Mendes',
                'email': 'carlos@empresa.com',
                'company': 'StartupTech',
                'message': 'Gostaria de saber mais sobre implementação de IA para e-commerce.',
                'status': 'new',
                'created_at': datetime.now()
            },
            {
                '_id': '2',
                'name': 'Ana Costa',
                'email': 'ana@consultoria.com',
                'company': 'ConsultPlus',
                'message': 'Interessada em parceria para projetos de automação.',
                'status': 'responded',
                'created_at': datetime.now()
            }
        ]
    
    def list_collection_names(self):
        return ['blog_posts', 'testimonials', 'contacts', 'users']

