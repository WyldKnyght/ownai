"""Test access to the vector store."""
import tempfile
import shutil
from flask import session
import pytest
from langchain.embeddings.base import Embeddings
from langchain.vectorstores.base import VectorStore
from backaind.db import get_db
from backaind.knowledge import (
    add_knowledge,
    get_embeddings,
    get_knowledge,
    get_all_knowledge_entries_from_db,
    get_knowledge_entry_from_db,
    KnowledgeConfigError,
)


def test_get_embeddings_raises_on_unknown_embeddings(client):
    """Test if an exception is raised when requesting an unknown embedding function."""
    with client:
        client.get("/")
        with pytest.raises(KnowledgeConfigError) as error:
            get_embeddings("unknown")

        assert str(error.value) == "Unknown embeddings type: unknown"


def test_get_embeddings_returns_embeddings(client):
    """Test if get_embeddings() returns an Embeddings instance."""
    with client:
        client.get("/")
        embeddings = get_embeddings("huggingface")
        assert isinstance(embeddings, Embeddings)


def test_get_knowledge_returns_vector_store(client):
    """Test if get_knowledge() returns a VectorStore instance."""
    knowledge_path = tempfile.mkdtemp()
    with client:
        client.get("/")
        knowledge = get_knowledge(1)
        assert isinstance(knowledge, VectorStore)
    shutil.rmtree(knowledge_path)


def test_get_knowledge_returns_from_session(client):
    """Test if get_knowledge() caches the instance in session."""
    with client:
        client.get("/")
        session["knowledge[1]"] = "NotRealKnowledge"
        knowledge = get_knowledge(1)
        assert knowledge == "NotRealKnowledge"


def test_get_knowledge_entry_from_db_returns_entry(app):
    """Test if get_knowledge_entry_from_db() returns an entry from the database."""
    with app.app_context():
        entry = get_knowledge_entry_from_db(1)
        assert entry["name"] == "Test 1"


def test_get_all_knowledge_entries_from_db_returns_all_entries(app):
    """Test if get_all_knowledge_entries_from_db() returns all entries from the database."""
    with app.app_context():
        entries = get_all_knowledge_entries_from_db()
        assert len(entries) == 2


def test_add_knowledge_command_adds_knowledge(app, runner):
    """Test if the add-knowledge command adds a new knowledge entry to the database."""
    knowledge_name = "Test"
    knowledge_embeddings = "huggingface"
    knowledge_persist_directory = "instance/knowledge-test"
    with app.app_context():
        database = get_db()

        knowledge_entry = database.execute(
            "SELECT * FROM knowledge WHERE name = ?", (knowledge_name,)
        ).fetchone()
        assert knowledge_entry is None

        result = runner.invoke(
            add_knowledge,
            input=f"{knowledge_name}\n{knowledge_embeddings}\n{knowledge_persist_directory}",
        )
        assert f"Added {knowledge_name}" in result.output

        knowledge_entry = database.execute(
            "SELECT * FROM knowledge WHERE name = ?", (knowledge_name,)
        ).fetchone()
        assert knowledge_entry is not None


def test_add_knowledge_command_updates_knowledge(app, runner):
    """Test if the add-knowledge command updates knowledge with the same name."""
    knowledge_name = "Test 1"
    knowledge_embeddings = "huggingface"
    knowledge_persist_directory = "instance/knowledge"
    with app.app_context():
        database = get_db()
        database.execute(
            "UPDATE knowledge SET persist_directory = 'old_directory' WHERE name = ?",
            (knowledge_name,),
        )

        knowledge_entry = database.execute(
            "SELECT * FROM knowledge WHERE name = ?", (knowledge_name,)
        ).fetchone()
        assert knowledge_entry["persist_directory"] == "old_directory"

        result = runner.invoke(
            add_knowledge,
            input=f"{knowledge_name}\n{knowledge_embeddings}\n{knowledge_persist_directory}",
        )
        assert f"Updated {knowledge_name}" in result.output

        knowledge_entry = database.execute(
            "SELECT * FROM knowledge WHERE name = ?", (knowledge_name,)
        ).fetchone()
        assert knowledge_entry["persist_directory"] == knowledge_persist_directory
