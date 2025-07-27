# C:/Development/Projects/Demented-Discord-Bot/setup.py

from setuptools import setup, find_packages

# Read the contents of your README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Define your project's core dependencies
# These are the packages required for the bot to run.
install_requires = [
    'py-cord[voice]',       # The Discord library with voice support
    'python-dotenv',        # For loading environment variables from .env files
    'aiohttp',              # For asynchronous HTTP requests (used by discord.py and session_manager)
    'requests',             # Standard library for making HTTP requests
    'waitress',             # Production-ready WSGI server for the keep_alive web server
    'transformers',         # For advanced sentiment analysis
    'torch',                # Required by transformers
    'nltk',                 # For fallback or other text processing tasks
    'gTTS',                 # --- NEW: For Text-to-Speech functionality ---
]

# Define dependencies for development and testing
# `pip install -e ".[dev]"` will install these
dev_requires = [
    'pylint',
    'black',
]

setup(
    name='demented-discord-bot',
    version='2.0.0',
    author='Your Name',  # Feel free to change this
    author_email='your.email@example.com',  # And this
    description='A feature-rich, AI-powered Discord bot with a unique personality.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/yourusername/Demented-Discord-Bot', # Change to your repo URL
    packages=find_packages(),
    install_requires=install_requires,
    extras_require={
        'dev': dev_requires,
    },
    python_requires='>=3.8',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License', # Or your chosen license
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Operating System :: OS Independent',
        'Topic :: Communications :: Chat',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
    ],
)