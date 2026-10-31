"""The web UI's preferences: `GET` and `PUT /api/v1/preferences`
(docs/specs/web-ui.md#preferences)."""

from coding_study.application.ports import PreferencesStore
from coding_study.domain.errors import UsageError
from coding_study.domain.preferences import Preferences, parse_preferences, preferences_document


def read_preferences(store: PreferencesStore) -> Preferences:
    """A missing or unreadable file means the defaults."""
    document = store.read()
    if document is None:
        return Preferences()
    try:
        return parse_preferences(document)
    except UsageError:
        return Preferences()


def save_preferences(store: PreferencesStore, document: object) -> Preferences:
    """Rewrites the whole file; raises UsageError, writing nothing, for an invalid document."""
    preferences = parse_preferences(document)
    store.write(preferences_document(preferences))
    return preferences
