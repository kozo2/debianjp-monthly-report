# User event registration pages.
# coding=utf-8
from google.appengine.api import users

import schema
import send_notification
import webapp_generic

class UserEventRegistrationPage(webapp_generic.WebAppGenericProcessor):
    """Form where user signs up for an event, and edits old sign-up entries."""
    def process_input(self):
        eventid = self.request.get('eventid')
        user = users.get_current_user()

        # try loading the item with same eventid from datastore
        event = self.load_event_with_eventid(eventid)
        if event == None:
            self.http_error_message('Event id %s not found' % (eventid))
            return

        user_realname = self.load_user_realname_with_userid(user)
        if user_realname == None:
            # if empty, create a new instance
            user_realname = schema.UserRealname()
            user_realname.user = user
            user_realname.realname = user.nickname()

        attendance = self.load_attendance_with_eventid_and_user(eventid, user)
        template_values = {
            'nickname': event.owner.nickname(),
            'eventid': event.eventid,
            'title': event.title,
            'location': event.location,
            'content': event.content,
            'content_url': event.content_url,
            'prework': event.prework,
            'event_date': event.event_date,
            }

        if attendance == None:
            # this is a new registration
            template_values['user_prework'] = ""
            template_values['user_attend'] = True
            template_values['user_enkai_attend'] = True
            template_values['user_realname'] = user_realname.realname
        else:
            # Editing an old registration entry
            template_values['user_prework'] = attendance.prework
            template_values['user_attend'] = attendance.attend
            template_values['user_enkai_attend'] = attendance.enkai_attend
            template_values['user_realname'] = attendance.user_realname

        self.template_render_output(template_values, 'UserEventRegistrationPage.html')

class UserCommitEventRegistration(webapp_generic.WebAppGenericProcessor):
    """The page to show after user commits to a registration."""
    def process_input(self):
        eventid = self.request.get('eventid')
        event = self.load_event_with_eventid(eventid)
        if event == None:
            self.http_error_message('Event id %s not found' % (eventid))
            return
        user = users.get_current_user()

        # update user_realname cache.
        user_realname = self.load_user_realname_with_userid(user)
        if user_realname == None:
            # if empty, create a new instance
            user_realname = schema.UserRealname()
            user_realname.user = user
        user_realname.realname = self.request.get('user_realname')
        user_realname.put()

        attendance = self.load_attendance_with_eventid_and_user(eventid, user)
        if attendance == None:
            # create new entry if it's not available yet, otherwise reuse an old entry.
            attendance = schema.Attendance()
        attendance.eventid = eventid
        attendance.user = user
        attendance.user_realname = user_realname.realname
        attendance.prework = self.request.get('user_prework')
        attendance.attend = (self.request.get('user_attend') == 'attend')
        attendance.enkai_attend = (self.request.get('user_enkai_attend') == 'enkai_attend')

        attendance.put()

        mail_title = "[Debian登録システム] %s が %s に登録しました" % (user.nickname(), event.title.encode('utf-8')) 
        
        mail_template = {
            'attendance': attendance,
            'event': event,
            'event_url': 'http://%s/event?eventid=%s' % (self.request.host, eventid),
            }
        mail_message = self.template_render(mail_template, 'UserCommitEventRegistration.txt')
        send_notification.send_notification_to_user_and_owner(user.email(), 
                                                              event.owner.email(), 
                                                              event.owners_email,
                                                              mail_title, mail_message)
        self.redirect('/thanks?eventid=%s' % (eventid))

