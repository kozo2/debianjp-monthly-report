# Wrappers for webapp.RequestHandler.
import os

from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

import schema

NO_SHOW_REMAINING_SEATS = -1 # return a fake value so that UI won't show the limit.
MEMCACHE_EXPIRE_TIME = 24 * 60 * 60 # Make it so that cache expires after 24 hours. Should be good enough?

class WebAppGenericProcessor(webapp.RequestHandler):
    """Convenience class to collect all methods that seem generally useful.

    Merge get and post requests so that both is handled by the same
    handler, process_input.
    """
    def process_input(self):
        """do something here"""

    def get(self):
        self.process_input()

    def post(self):
        self.process_input()

    def event_memcache_key(self, eventid):
        """obtain memcached key for event."""
        key = 'load_event_with_eventid %s' % eventid
        return key

    def load_event_with_eventid(self, eventid):
        """Load an event with the eventid.
        """
        events = schema.Event.gql('WHERE eventid = :1 ORDER BY timestamp DESC LIMIT 1', eventid)
        event = events.get()
        return event

    def load_event_with_eventid_cached(self, eventid):
        """Load an event with the eventid, with memcache.
        """
        key = self.event_memcache_key(eventid)
        data = memcache.get(key)
        if data is not None:
            return data
        else:
            data = self.load_event_with_eventid(eventid)
            memcache.add(key, data, MEMCACHE_EXPIRE_TIME)
            return data

    def invalidate_event_with_eventid(self, eventid):
        """Invalidate an event memcache for eventid, should be called when data is updated."""
        key = self.event_memcache_key(eventid)
        memcache.delete(key)

    def fixup_attendance(self, attendance):
        """Fixup attendance after loading.

        Try to cover migration where attendance.prework -> attendance.prework_text
        """
        if attendance.prework_text is None:
            attendance.prework_text = attendance.prework

    def load_attendance_with_eventid_and_user(self, eventid, user):
        """Load an attendance with the eventid and user."""
        attendances = schema.Attendance.gql('WHERE eventid = :1 and user = :2 ORDER BY timestamp DESC LIMIT 1', 
                                            eventid, user)
        attendance = attendances.get()
        if attendance:
            self.fixup_attendance(attendance)
        return attendance

    def load_event_title_with_eventid_cached(self, eventid):
        """Load an event title with the eventid.
        """
        event = self.load_event_with_eventid_cached(eventid)
        return event.title

    def load_user_realname_with_userid(self, user):
        """Load corresponding user_realname object with matching user
        """
        user_realnames = schema.UserRealname.gql('WHERE user = :1 ORDER BY timestamp DESC LIMIT 1', 
                                                 user)
        user_realname = user_realnames.get()
        return user_realname

    def load_users_with_eventid(self, eventid):
        """Load list of users, and number of attendances from eventid."""
        attendances = schema.Attendance.gql('WHERE eventid = :1 ORDER BY timestamp DESC', 
                                            eventid).fetch(1000)
        num_attend = 0
        num_enkai_attend = 0
        for attendance in attendances:
            self.fixup_attendance(attendance)
            if attendance.attend:
                num_attend += 1
            if attendance.enkai_attend:
                num_enkai_attend += 1
        return (attendances, num_attend, num_enkai_attend)

    def check_auth_owner(self, event):
        """Check if this user is an owner of this event, 
        or the email is listed in owner_email list."""
        user = users.get_current_user()
        if event.owner == user:
            return True
        for owner_email in event.owners_email:
            if owner_email == user.email():
                return True
        return False

    def template_render(self, template_values, template_filename):
        """render using template."""
        path = os.path.join(os.path.dirname(__file__), template_filename)
        return template.render(path, template_values)

    def template_render_output(self, template_values, template_filename):
        """Convenience function to send out template results"""
        rendered_output = self.template_render(template_values, template_filename)
        self.response.out.write(rendered_output)

    def http_error_message(self, message):
        """output error message and return http error message."""
        self.response.set_status(404)
        self.response.out.write(message)

    def count_remaining_seats(self, eventid, capacity):
        """count the remaining seats
        """
        if capacity > 0:
            attendances, num_attend, num_enkai_attend = self.load_users_with_eventid(eventid)
            return max(capacity - num_attend, 0)
        else:
            return NO_SHOW_REMAINING_SEATS