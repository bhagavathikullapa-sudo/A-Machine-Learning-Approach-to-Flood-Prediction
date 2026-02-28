from app import app, db, User

with app.app_context():
    # Find user by email
    user = User.query.filter_by(email="abbugunasekhar@gmail.com").first()
    
    if user:
        print(f"Deleting user: {user.name} ({user.email})")
        db.session.delete(user)
        db.session.commit()
        print("User deleted successfully!")
    else:
        print("User not found!")