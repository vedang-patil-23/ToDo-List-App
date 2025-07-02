from app import app, db, User

def init_db():
    with app.app_context():
        db.create_all()
        if User.query.first() is None:
            admin = User(username='admin', password='admin123')
            viewer = User(username='viewer', password='view123')
            db.session.add(admin)
            db.session.add(viewer)
            db.session.commit()
            print("Default users created:")
            print("Admin - Username: admin, Password: admin123")
            print("Viewer - Username: viewer, Password: view123")

if __name__ == '__main__':
    init_db() 