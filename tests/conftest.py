"""Fixtures pytest partagées — BDD éphémère SQLite par test.

Le binôme étend ce module si besoin pour les tests d'ingestion.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.models import Base


@pytest.fixture
def tmp_db_url() -> str:
    """Crée une BDD SQLite temporaire et retourne son URL.
    
    Sur Windows, utilise une BDD en mémoire pour éviter les problèmes de locking.
    """
    # Utilise :memory: pour éviter les problèmes de fichier temporaire sur Windows
    yield "sqlite:///:memory:"


@pytest.fixture
def tmp_engine(tmp_db_url):
    """Engine SQLAlchemy sur la BDD temporaire, schéma créé.
    
    Configure SQLite pour fonctionner correctement avec une BDD en mémoire.
    """
    # Pour :memory:, utilise StaticPool pour que la connexion persiste
    engine = create_engine(
        tmp_db_url,
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield engine
    # Ferme toutes les connexions ouvertes
    engine.dispose()


@pytest.fixture
def tmp_session(tmp_engine):
    """Session SQLAlchemy à utiliser dans les tests d'ingestion."""
    Session = sessionmaker(bind=tmp_engine, autoflush=False)
    session = Session()
    yield session
    session.close()
