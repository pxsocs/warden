# This is a mesage handler. All messages that need to be
# temporary saved and later accessed through the app can
# be structured here.
# It's recommended to start the handler as an instance of the Flask App
# that can be later accessed anywhere
# current_app.message_handler = MessageHandler()
# Messages are stored in a pickle file that can be updated in the backgound
import os
import random
from datetime import datetime
from pathlib import Path
from utils import pickle_it


class Message():
    def __init__(self, category, message_txt, message_html, notes, data=None):
        self.id = random.getrandbits(16)
        self.time = datetime.now()
        self.category = category
        self.message_txt = message_txt
        self.message_html = message_html
        self.notes = notes
        self.data = data


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
        return(messages)

    def saver(self):
        pickle_it(action='save', filename=self.filename, data=self.messages)

    def clean_all(self):
        # Delete the pkl file
        try:
            os.remove(self.filepath)
        except FileNotFoundError:
            pass
        self.messages = []

    def add_message(self, message):
        self.messages.append(message)
        self.saver()

    def pop_message(self, message):
        self.messages = [item for item in self.messages if item != message]
        self.saver()

    def list_messages(self):
        for message in self.messages:
            print(message)
