#!/usr/bin/env python

"""main.py - This file contains handlers that are called by taskqueue and/or
cronjobs."""
import logging
import webapp2
from google.appengine.api import mail, app_identity
from api import BattleshipApi

from models import User, Game


class SendEmail(webapp2.RequestHandler):
    def post(self):
        user_name = self.request.get('user_name')
        user_email = self.request.get('user_email')
        game_key = self.request.get('game_key')
        message = self.request.get('message')
        app_id = app_identity.get_application_id()

        subject = 'Your turn!'
        body = 'Hello {}, you have a message regarding your Battleship game with id {}!'.format(user_name, game_key)
        body += '\n \n' + message + '\n \n Good luck!'
        # This will send test emails, the arguments to send_mail are:
        # from, to, subject, body
        mail.send_mail('noreply@{}.appspotmail.com'.format(app_id),
                       user_email,
                       subject,
                       body)

class SendReminderEmail(webapp2.RequestHandler):
    def get(self):

        app_id = app_identity.get_application_id()
        open_games = Game.query(Game.status.IN(['p1 move','p2 move'])).fetch()

        emails_to_send = []
        for g in open_games:
            if g.status == 'p1 move':
                user_email = g.p1.get().email
            elif g.status == 'p2 move':
                user_email = g.p2.get().email
            if user_email:
                emails_to_send.append((user_email, g.key.urlsafe()))

        for e in emails_to_send:
            subject = 'Your turn!'
            body = 'Just a reminder: It\'s your turn in the Battleship game with id {}!'.format(e[1])

            # from, to, subject, body
            mail.send_mail('noreply@{}.appspotmail.com'.format(app_id),
                           e[0],
                           subject,
                           body)


app = webapp2.WSGIApplication([
    ('/sendemail', SendEmail),
    ('/crons/send_reminder', SendReminderEmail)
], debug=True)
