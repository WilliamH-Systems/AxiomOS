import os
import sys
from src.agent import axiom_agent
from src.database import db_manager
from src.redis_manager import redis_manager


def main():
    print("AxiomOS - Personal Assistant")
    print("=" * 50)

    # Check database connections
    print("Checking connections...")

    # Check Redis
    if redis_manager.ping():
        print("✅ Redis connection successful")
    else:
        print("❌ Redis connection failed - using memory fallback")

    # Create database tables
    try:
        db_manager.create_tables()
        print("✅ Database tables created/verified")
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        print("   Note: PostgreSQL may not be installed. Using memory fallback.")

    print("\nAxiomOS is ready! Type 'quit' to exit.")
    print("-" * 50)

    session_id = None

    while True:
        try:
            user_input = input("\nYou: ").strip()

            if user_input.lower() in ["quit", "exit", "q"]:
                print("👋 Goodbye!")
                break

            if not user_input:
                continue

            # Process the message through AxiomOS
            result = axiom_agent.run(user_input, session_id)

            print(f"\nAxiomOS: {result['response']}")

            # Update session ID for continuity
            session_id = result["session_id"]

            # Show context info if available
            if result.get("context"):
                context_keys = list(result["context"].keys())
                if context_keys:
                    print(f"   (Context: {', '.join(context_keys)})")

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("   Please try again.")


if __name__ == "__main__":
    main()
