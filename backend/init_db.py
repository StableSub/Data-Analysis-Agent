from app.core.db import Base, engine   

#로컬 DB 재생성
print("⚙️ Dropping all tables...")
Base.metadata.drop_all(bind=engine)

print("🛠 Creating all tables...")
Base.metadata.create_all(bind=engine)

print("🎉 Database initialized successfully!")