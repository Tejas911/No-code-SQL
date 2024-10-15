import streamlit as st
from langchain.agents import create_sql_agent
from langchain.sql_database import SQLDatabase
from langchain.agents.agent_types import AgentType
from langchain.callbacks import StreamlitCallbackHandler
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from sqlalchemy import create_engine
from langchain_groq import ChatGroq
from langchain_ollama.llms import OllamaLLM


st.set_page_config(page_title="Chat with SQL DB", page_icon="🤖")
st.title("Chat with SQL DB")

MYSQL = "USE_MYSQL"

# Sidebar options
selected_opt = "Connect to your MySQL Database"

# Gather MySQL credentials
mysql_host = st.sidebar.text_input("MySQL Host")
mysql_user = st.sidebar.text_input("MySQL User")
mysql_password = st.sidebar.text_input("MySQL Password", type="password")
mysql_db = st.sidebar.text_input("MySQL Database")

db_uri = MYSQL

# API key for Groq model
api_key = st.sidebar.text_input(label="GRoq API Key", type="password")

# Error messages for missing credentials
if not db_uri:
    st.info("Please enter the database information and URI")

if not api_key:
    st.info("Please add the Groq API key")

# LLM model
llm = ChatGroq(groq_api_key=api_key, model_name="Llama3-8b-8192", streaming=True)

# Ollama model
# llm = OllamaLLM(model="llama3.1")


@st.cache_resource(ttl="2h")
def configure_db(db_uri, mysql_host, mysql_user, mysql_password, mysql_db):
    # Ensure all MySQL credentials are provided
    if not (mysql_host and mysql_user and mysql_password and mysql_db):
        st.error("Please provide all MySQL connection details.")
        st.stop()
    connection_string = (
        f"mysql+mysqlconnector://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_db}"
    )
    return SQLDatabase(create_engine(connection_string))


# Configure the database based on the user's selection
db = configure_db(db_uri, mysql_host, mysql_user, mysql_password, mysql_db)

# Toolkit setup
toolkit = SQLDatabaseToolkit(db=db, llm=llm)

# Agent setup
agent = create_sql_agent(
    llm=llm,
    toolkit=toolkit,
    verbose=True,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
)

# Handle session state for messages
if "messages" not in st.session_state or st.sidebar.button("Clear message history"):
    st.session_state["messages"] = [
        {"role": "assistant", "content": "How can I help you?"}
    ]

# Display messages in the chat interface
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Get the user's query
user_query = st.chat_input(placeholder="Ask anything from the database")

# Process the user query and respond
if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})
    st.chat_message("user").write(user_query)

    with st.chat_message("assistant"):
        streamlit_callback = StreamlitCallbackHandler(st.container())
        response = agent.run(user_query, callbacks=[streamlit_callback])
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.write(response)
