from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.prompts import (SystemMessagePromptTemplate, 
                                    HumanMessagePromptTemplate, 
                                    ChatPromptTemplate,
                                    PromptTemplate,
                                    MessagesPlaceholder)
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

base_url = "http://localhost:11434/"
model_name = "llama3.2:1b"

llm = ChatOllama(
    base_url = base_url,
    model = model_name
)

system_prompt = SystemMessagePromptTemplate.from_template("You are a helpful AI assistant that answers user question based on the provided context.")

human_prompt = """
Answer user question based on the provided context ONLY! If you do not know the answer, just say "I don't know".
### Context:
{context}

### Question:
{question}

### Answer:
"""
human_prompt = HumanMessagePromptTemplate.from_template(human_prompt)

template = ChatPromptTemplate([system_prompt, human_prompt])

qna_chain = template | llm | StrOutputParser()

def ask_llm(context, question):
  response = qna_chain.invoke({'context': context, 'question': question})
  return response