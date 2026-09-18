"""
Custom exceptions for ATLAS / Study Sentinel
"""

class AtlasError(Exception):
    """Base exception for ATLAS platform"""
    pass

class StudyNotFoundError(AtlasError):
    pass

class SubjectNotFoundError(AtlasError):
    pass

class RecordNotFoundError(AtlasError):
    pass

class CutNotFoundError(AtlasError):
    pass

class ReferenceRangeNotFoundError(AtlasError):
    pass
