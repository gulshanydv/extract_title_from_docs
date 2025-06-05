import openai
from dotenv import load_dotenv
import os
import mysql.connector
from datetime import datetime
import json

load_dotenv()

# Set your OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "anviam",
    "database": "employee_data"
}

# Define your database schema
schema_description = """
You are an assistant that converts natural language into SQL queries.

Here is the database schema:
Table: patients_personal_details
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    uuid VARCHAR(255) COLLATE utf8mb4_unicode_ci,
    mob_db_id VARCHAR(255) COLLATE utf8mb4_unicode_ci,
    patient_id VARCHAR(255) COLLATE utf8mb4_unicode_ci,
    name VARCHAR(255) COLLATE utf8mb4_unicode_ci NOT NULL,
    age INT,
    height INT,
    weight INT,
    avatar VARCHAR(255) COLLATE utf8mb4_unicode_ci,
    blood VARCHAR(255) COLLATE utf8mb4_unicode_ci,
    gender VARCHAR(255) COLLATE utf8mb4_unicode_ci,
    date VARCHAR(255) COLLATE utf8mb4_unicode_ci,
    location VARCHAR(255) COLLATE utf8mb4_unicode_ci,
    patient_type VARCHAR(255) COLLATE utf8mb4_unicode_ci,
    symptoms LONGTEXT COLLATE utf8mb4_unicode_ci,
    note LONGTEXT COLLATE utf8mb4_unicode_ci,
    time_slot VARCHAR(255) COLLATE utf8mb4_unicode_ci,
    current_medication VARCHAR(255) COLLATE utf8mb4_unicode_ci,
    policy_enrolled VARCHAR(255) COLLATE utf8mb4_unicode_ci,
    doctor_id INT,
    organisation_id BIGINT UNSIGNED,
    assign_to INT,
    created_by_id INT,
    created_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL,
    deleted_at TIMESTAMP NULL,
    session_type INT,
    last_activity LONGTEXT COLLATE utf8mb4_unicode_ci,
    other_field_values LONGTEXT COLLATE utf8mb4_unicode_ci

Additional Context:
- When user refers to "patients", they likely mean "patient_personal_details" (assuming this is for a healthcare organization)
- When user asks follow-up questions, consider the previous context and queries
"""

class ConversationalSQLAssistant:
    def __init__(self):
        self.conversation_history = []
        self.query_results_cache = {}
        
    def add_to_history(self, user_input, sql_query, results=None, error=None):
        """Add interaction to conversation history"""
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "sql_query": sql_query,
            "results": results,
            "error": error
        }
        self.conversation_history.append(history_entry)
        
    def get_context_from_history(self):
        """Generate context string from conversation history"""
        if not self.conversation_history:
            return ""
            
        context = "\n\nPrevious conversation context:\n"
        for i, entry in enumerate(self.conversation_history[-5:], 1):  # Last 5 interactions
            context += f"{i}. User asked: '{entry['user_input']}'\n"
            context += f"   Generated SQL: {entry['sql_query']}\n"
            if entry['results']:
                # Limit results display for context
                results_preview = str(entry['results'][:3]) + "..." if len(entry['results']) > 3 else str(entry['results'])
                context += f"   Results: {results_preview}\n"
            if entry['error']:
                context += f"   Error: {entry['error']}\n"
            context += "\n"
        return context
    
    def natural_language_to_sql(self, nl_query):
        """Convert natural language to SQL with conversation context"""
        context = self.get_context_from_history()
        
        prompt = f"""
        You are an assistant that converts natural language into SQL queries.

        Here is the database schema:

        Table: patient_personal_details
        - id (BIGINT, Primary Key, Auto Increment)
        - uuid (VARCHAR): Unique universal identifier
        - mob_db_id (VARCHAR): Mobile DB reference
        - patient_id (VARCHAR): External or hospital patient ID
        - name (VARCHAR): Patient's full name
        - age (INT): Patient's age
        - height (INT): Patient's height in cm
        - weight (INT): Patient's weight in kg
        - avatar (VARCHAR): URL to avatar/profile image
        - blood (VARCHAR): Blood group (e.g., A+, B-)
        - gender (VARCHAR): Gender of the patient
        - date (VARCHAR): Visit or admission date
        - location (VARCHAR): Physical location of the patient or visit
        - patient_type (VARCHAR): Type/category of patient (e.g., outpatient, inpatient)
        - symptoms (LONGTEXT): Symptoms described by the patient
        - note (LONGTEXT): Additional medical or personal notes
        - time_slot (VARCHAR): Appointment or session time slot
        - current_medication (VARCHAR): Ongoing medications
        - policy_enrolled (VARCHAR): Insurance or health policy details
        - doctor_id (INT): Associated doctor's ID
        - organisation_id (BIGINT): Related organization ID
        - assign_to (INT): ID of assigned staff or system
        - created_by_id (INT): ID of user who created the record
        - created_at (TIMESTAMP): Record creation time
        - updated_at (TIMESTAMP): Last update timestamp
        - deleted_at (TIMESTAMP): Deletion timestamp (if soft deleted)
        - session_type (INT): Type of session (e.g., 1 for video, 2 for audio)
        - last_activity (LONGTEXT): Description of the last activity
        - other_field_values (LONGTEXT): JSON or extended data fields

        Additional Context:
        - Use only this table when generating queries
        - When user refers to "patients", interpret them directly as entries in this table
        - If the user asks for "names", select the `name` column
        - If the user asks about time, appointment, or sessions, refer to `date`, `time_slot`, and `session_type`
        - If the user asks for filters like age, gender, or blood group, use corresponding fields
        - If the user asks "how many", return a COUNT query
        - Follow-up questions may refer to earlier queries, so include {context} if relevant
        - Use standard SQL syntax
        - Output only the SQL query—no explanations or commentary

        {context}

        Based on the schema and previous conversation context, convert the following natural language question into a SQL query.
        Consider any references to previous queries or results.

        Current Question: "{nl_query}"

        SQL Query:
        """

        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that writes SQL queries based on natural language and conversation context. Return only the SQL query."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=200
            )
            
            sql_query = response['choices'][0]['message']['content'].strip()
            # Clean up the response to get only SQL
            if sql_query.startswith('```sql'):
                sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
            elif sql_query.startswith('```'):
                sql_query = sql_query.replace('```', '').strip()
                
            return sql_query
            
        except Exception as e:
            print(f"Error generating SQL: {e}")
            return None

    def execute_sql_query(self, sql_query):
        """Execute SQL query and return results"""
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute(sql_query)

            if cursor.with_rows:
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                
                print(f"\nQuery Results ({len(rows)} rows):")
                print("-" * 50)
                
                # Print column headers
                print(" | ".join(f"{col:15}" for col in columns))
                print("-" * (len(columns) * 18))
                
                # Print rows
                for row in rows:
                    print(" | ".join(f"{str(val):15}" for val in row))
                
                return rows
            else:
                conn.commit()
                print("Query executed successfully (no return rows).")
                return []

        except mysql.connector.Error as err:
            print("MySQL Error:", err)
            return None

        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def process_query(self, user_input):
        """Process a user query with context awareness"""
        print(f"\n{'='*60}")
        print(f"Processing: {user_input}")
        print(f"{'='*60}")
        
        # Generate SQL query
        sql_query = self.natural_language_to_sql(user_input)
        
        if not sql_query:
            print("Failed to generate SQL query.")
            return
            
        print(f"\nGenerated SQL Query:\n{sql_query}")
        
        # Execute query
        results = self.execute_sql_query(sql_query)
        
        # Add to history
        error = None if results is not None else "Query execution failed"
        self.add_to_history(user_input, sql_query, results, error)
        
        return results

    def show_history(self):
        """Display conversation history"""
        if not self.conversation_history:
            print("No conversation history yet.")
            return
            
        print("\n" + "="*80)
        print("CONVERSATION HISTORY")
        print("="*80)
        
        for i, entry in enumerate(self.conversation_history, 1):
            print(f"\n{i}. [{entry['timestamp']}]")
            print(f"   User: {entry['user_input']}")
            print(f"   SQL: {entry['sql_query']}")
            if entry['results']:
                result_count = len(entry['results']) if isinstance(entry['results'], list) else 0
                print(f"   Results: {result_count} rows returned")
            if entry['error']:
                print(f"   Error: {entry['error']}")

    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        self.query_results_cache = {}
        print("Conversation history cleared.")

# Enhanced main function with interactive features
def main():
    assistant = ConversationalSQLAssistant()
    
    print("="*80)
    print("CONVERSATIONAL SQL ASSISTANT")
    print("="*80)
    print("Ask questions in natural language. I'll remember our conversation!")
    print("\nSpecial commands:")
    print("- 'history' : Show conversation history")
    print("- 'clear' : Clear conversation history")  
    print("- 'quit' or 'exit' : Exit the program")
    print("="*80)
    
    while True:
        try:
            user_input = input("\n🤖 Ask me anything: ").strip()
            
            if not user_input:
                continue
                
            # Handle special commands
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye! 👋")
                break
            elif user_input.lower() == 'history':
                assistant.show_history()
                continue
            elif user_input.lower() == 'clear':
                assistant.clear_history()
                continue
            
            # Process the query
            assistant.process_query(user_input)
            
        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"An error occurred: {e}")

# Example usage scenarios
def run_examples():
    """Run some example scenarios to demonstrate the functionality"""
    assistant = ConversationalSQLAssistant()
    
    print("Running example scenarios...")
    
    # Example 1: Basic query
    print("\n" + "="*50)
    print("EXAMPLE 1: Basic Query")
    assistant.process_query("How many employees are there?")
    
    # Example 2: Follow-up query
    print("\n" + "="*50)
    print("EXAMPLE 2: Follow-up Query")
    assistant.process_query("Give me their names")
    
    # Example 3: Context-aware query
    print("\n" + "="*50)
    print("EXAMPLE 3: Context-aware Query")
    assistant.process_query("What are their salaries?")
    
    # Show history
    assistant.show_history()

if __name__ == "__main__":
    # Uncomment the next line to run examples
    # run_examples()
    
    # Run the interactive assistant
    main()