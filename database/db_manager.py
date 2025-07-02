from mongoengine import connect, disconnect
from config import DATABASE_URL

def connect_db():
    try:
        connect(host=DATABASE_URL)
        print("Connected to MongoDB.")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")

def disconnect_db():
    disconnect()
    print("Disconnected from MongoDB.")

# Example usage (can be removed later)
if __name__ == "__main__":
    connect_db()
    # You can add some test operations here
    disconnect_db()