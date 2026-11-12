"""Accent color palette shared by forms, routes and templates.

Keys are stored in UserSettings.accent_color (String(10)), so keep them <= 10 chars.
`bright` is used as the text/link color in dark mode, so it must stay readable on dark backgrounds.
"""

ACCENT_COLORS = {
    'purple':     {'label': 'Purple',      'primary': '#6f42c1', 'dark': '#5a359a', 'light': '#8e63d4', 'bright': '#c4a8ff', 'rgb': '111, 66, 193'},
    'darkpurple': {'label': 'Dark Purple', 'primary': '#4a1d7a', 'dark': '#36155a', 'light': '#6b3fa0', 'bright': '#b794f6', 'rgb': '74, 29, 122'},
    'blue':       {'label': 'Blue',        'primary': '#007bff', 'dark': '#0056b3', 'light': '#66b3ff', 'bright': '#7cbcff', 'rgb': '0, 123, 255'},
    'teal':       {'label': 'Teal',        'primary': '#0f8b8d', 'dark': '#0b6b6d', 'light': '#3fb0b2', 'bright': '#6fe0e2', 'rgb': '15, 139, 141'},
    'green':      {'label': 'Green',       'primary': '#28a745', 'dark': '#1e7e34', 'light': '#5cb85c', 'bright': '#6fdc8c', 'rgb': '40, 167, 69'},
    'orange':     {'label': 'Orange',      'primary': '#e8590c', 'dark': '#c2410c', 'light': '#fd7e14', 'bright': '#ffa94d', 'rgb': '232, 89, 12'},
    'red':        {'label': 'Red',         'primary': '#d32f2f', 'dark': '#b71c1c', 'light': '#e53935', 'bright': '#ff6b6b', 'rgb': '211, 47, 47'},
    'darkred':    {'label': 'Dark Red',    'primary': '#8b0000', 'dark': '#650000', 'light': '#b22222', 'bright': '#ff7a7a', 'rgb': '139, 0, 0'},
}

DEFAULT_ACCENT = 'purple'

ACCENT_CHOICES = [(key, value['label']) for key, value in ACCENT_COLORS.items()]


def get_accent(key):
    """Return the palette for `key`, falling back to the default accent."""
    return ACCENT_COLORS.get(key) or ACCENT_COLORS[DEFAULT_ACCENT]
