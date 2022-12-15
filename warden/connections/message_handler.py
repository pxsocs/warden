# This is a mesage handler. All messages that need to be
# temporary saved and later accessed through the app can
# be structured here.
# It's recommended to start the handler as an instance of the Flask App
# that can be later accessed anywhere
# current_app.message_handler = MessageHandler()
# Messages are stored in a pickle file that can be updated in the backgound

# List of categories and where they are displayed
# testing_specter:      tests specter connectivity and auth - shows
#                       at the specter connect / test page
import os
import random
from datetime import datetime
from pathlib import Path
from backend.utils import pickle_it
from ansi_management import time_ago
import json


class Message():

    def __init__(self,
                 category='',
                 message_txt='',
                 message_html='',
                 notes='',
                 data=None):
        self.id = random.getrandbits(16)
        self.time = datetime.now()
        self.time_str = self.time.strftime('%m/%d, %H:%M:%S')
        self.category = category
        self.message_txt = message_txt
        self.message_html = message_html
        self.notes = notes
        self.data = data
        if not message_html:
            message_html = '<p>' + self.message_txt + '</p>'


class MessageHandler():

    def __init__(self):
        home_path = Path.home()
        home_dir = os.path.join(home_path, 'warden')
        self.filename = 'message_handler.pkl'
        self.filepath = os.path.join(home_dir, self.filename)
        self.messages = self.loader()

    def loader(self):
        # Try loading pickle, if error return empty list
        pickle = pickle_it(action='load', filename=self.filename)
        if pickle == 'file not found':
            pickle = []
        messages = pickle
        return (messages)

    def saver(self):
        pickle_it(action='save', filename=self.filename, data=self.messages)

    def clean_all(self):
        # Delete the pkl file
        try:
            os.remove(self.filepath)
        except FileNotFoundError:
            pass
        self.messages = []

    # Removes all messages from a given category
    def clean_category(self, category):
        self.messages = [
            item for item in self.messages if item.category != category
        ]
        self.saver()

    def add_message(self, message):
        self.messages.append(message)
        self.saver()

    def pop_message(self, message):
        self.messages = [item for item in self.messages if item != message]
        self.saver()

    def list_messages(self):
        for message in self.messages:
            print(message)

    def to_json(self, category=None, sort_reverse=True):
        from backend.utils import safe_serialize
        sorted_messages = sorted(self.messages,
                                 key=lambda x: x.time,
                                 reverse=sort_reverse)
        if category:
            o = [
                item.__dict__ for item in sorted_messages
                if item.category == category
            ]
        else:
            o = [item.__dict__ for item in sorted_messages]
        return (safe_serialize(o))
