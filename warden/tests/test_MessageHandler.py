# Run unit tests from the warden directory:
# $ python3 test_Specter.py

import unittest
import os
import json
from connections.message_handler import Message, MessageHandler


class TestMessageHandler(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Include test messages here
        message_1 = {
            'category': 'test_specter',
            'message_txt': 'Testing Ping...',
            'message_html': '<pre>Testing Ping...</pre>',
            'notes': 'Testing the Message handler'
        }

        message_2 = {
            'category': 'test_specter_2',
            'message_txt': 'Testing Ping 2...',
            'message_html': '<pre>Testing Ping 2...</pre>',
            'notes': 'Testing the Message handler 2'
        }

        cls.messagehandler = MessageHandler()
        # Include messages
        cls.message_1 = Message(**message_1)
        cls.messagehandler.add_message(cls.message_1)
        cls.message_2 = Message(**message_2)
        cls.messagehandler.add_message(cls.message_2)

    def test_messages(self):
        # Test if anything was loaded
        loaded = self.messagehandler.messages
        self.assertIsInstance(loaded, list)
        # Make sure file was created
        self.assertTrue(os.path.isfile(self.messagehandler.filepath))

        self.assertIn(self.message_1, self.messagehandler.messages)
        self.assertIn(self.message_2, self.messagehandler.messages)
        # test Json w/ filter, reloads and checks contents
        json_tst = json.loads(
            self.messagehandler.to_json(category=self.message_1.category))
        self.assertEqual(json_tst[0]['message_txt'],
                         self.message_1.message_txt)
        # Remove msg1
        self.messagehandler.pop_message(self.message_1)
        # Check that it's not there
        self.assertNotIn(self.message_1, self.messagehandler.messages)
        # But msg2 should be there
        self.assertIn(self.message_2, self.messagehandler.messages)

        # Test Cleaning of all messages
        self.messagehandler.clean_all()
        # file exists?
        self.assertFalse(os.path.isfile(self.messagehandler.filepath))
        # messages there?
        self.assertNotIn(self.message_1, self.messagehandler.messages)
        self.assertNotIn(self.message_2, self.messagehandler.messages)


if __name__ == '__main__':
    print("Running tests... Please wait...")

    unittest.main()
