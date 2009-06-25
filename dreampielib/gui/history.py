import gtk
from gtk import gdk

from .tags import COMMAND, PROMPT

class History(object):
    """
    Manage moving between commands on the text view, and recalling commands
    in the source view.
    """
    def __init__(self, textview, sourceview):
        self.textview = textview
        self.textbuffer = textview.get_buffer()
        self.sourceview = sourceview
        self.sourcebuffer = sourceview.get_buffer()

        tb = self.textbuffer

        self.hist_prefix = None
        self.sb_changed = True
        # A handler_id when sb_changed is False.
        self.changed_handler_id = None
        self.hist_mark = tb.create_mark('history', tb.get_end_iter(), False)

    def _track_change(self):
        """Set self.sb_changed to False, and add a handler which will set it
        to True on the next change."""
        if not self.sb_changed:
            return
        self.sb_changed = False
        self.changed_handler_id = self.sourcebuffer.connect(
            'changed', self._on_sourcebuffer_changed)

    def _on_sourcebuffer_changed(self, widget):
        self.sb_changed = True
        self.sourcebuffer.disconnect(self.changed_handler_id)
        self.changed_handler_id = None

    def _iter_get_command(self, it, only_first_line=False):
        """Get a textiter placed inside (or at the end of) a COMMAND tag.
        Return the text of the tag which doesn't have the PROMPT tag.
        """
        tb = self.textbuffer
        prompt = tb.get_tag_table().lookup(PROMPT)
        command = tb.get_tag_table().lookup(COMMAND)

        it = it.copy()
        if not it.begins_tag(command):
            it.backward_to_tag_toggle(command)
            assert it.begins_tag(command)
        it_end = it.copy(); it_end.forward_to_tag_toggle(command)
        if it.has_tag(prompt):
            it.forward_to_tag_toggle(prompt)
        if it.compare(it_end) >= 0:
            # nothing but prompt
            return ''
        r = []
        while True:
            it2 = it.copy()
            it2.forward_to_tag_toggle(prompt)
            if it2.compare(it_end) >= 0:
                it2 = it.copy()
                it2.forward_to_tag_toggle(command)
                r.append(tb.get_text(it, it2))
                break
            r.append(tb.get_text(it, it2))
            if only_first_line:
                break
            it = it2
            it.forward_to_tag_toggle(prompt)
            if it.compare(it_end) >= 0:
                break
        return ''.join(r)

    def copy_to_sourceview(self):
        # Copy the current command to the sourceview
        tb = self.textbuffer
        command = tb.get_tag_table().lookup(COMMAND)

        it = tb.get_iter_at_mark(tb.get_insert())
        if not it.has_tag(command) and not it.ends_tag(command):
            gdk.beep()
            return True
        s = self._iter_get_command(it)
        if not s:
            gdk.beep()
            return True
        self.sourcebuffer.set_text(s)
        self.sourceview.grab_focus()
        return True

    def history_up(self):
        """Called when the history up command is required"""
        if self.textview.is_focus():
            tb = self.textbuffer
            command = tb.get_tag_table().lookup(COMMAND)
            insert = tb.get_insert()
            it = tb.get_iter_at_mark(insert)
            it.backward_to_tag_toggle(command)
            if it.ends_tag(command):
                it.backward_to_tag_toggle(command)
            self.textbuffer.place_cursor(it)
            self.textview.scroll_mark_onscreen(insert)

        elif self.sourceview.is_focus():
            tb = self.textbuffer
            sb = self.sourcebuffer
            command = tb.get_tag_table().lookup(COMMAND)
            if self.sb_changed:
                if sb.get_end_iter().get_line() != 0:
                    # Don't allow prefixes of more than one line
                    gdk.beep()
                    return
                self.hist_prefix = sb.get_text(sb.get_start_iter(),
                                               sb.get_end_iter())
                self._track_change()
                tb.move_mark(self.hist_mark, tb.get_end_iter())
            it = tb.get_iter_at_mark(self.hist_mark)
            if it.is_start():
                gdk.beep()
                return
            while True:
                it.backward_to_tag_toggle(command)
                if it.ends_tag(command):
                    it.backward_to_tag_toggle(command)
                if not it.begins_tag(command):
                    gdk.beep()
                    break
                first_line = self._iter_get_command(it, only_first_line=True)
                if first_line and first_line.startswith(self.hist_prefix):
                    command = self._iter_get_command(it)
                    sb.set_text(command)
                    sb.place_cursor(sb.get_end_iter())
                    self._track_change()
                    tb.move_mark(self.hist_mark, it)
                    break
                if it.is_start():
                    gdk.beep()
                    return

        else:
            gdk.beep()

    def history_down(self):
        """Called when the history down command is required"""
        if self.textview.is_focus():
            tb = self.textbuffer
            command = tb.get_tag_table().lookup(COMMAND)
            insert = tb.get_insert()
            it = tb.get_iter_at_mark(insert)
            it.forward_to_tag_toggle(command)
            if it.ends_tag(command):
                it.forward_to_tag_toggle(command)
            self.textbuffer.place_cursor(it)
            self.textview.scroll_mark_onscreen(insert)

        elif self.sourceview.is_focus():
            tb = self.textbuffer
            sb = self.sourcebuffer
            command = tb.get_tag_table().lookup(COMMAND)
            if self.sb_changed:
                gdk.beep()
                return
            it = tb.get_iter_at_mark(self.hist_mark)
            while True:
                it.forward_to_tag_toggle(command)
                it.forward_to_tag_toggle(command)
                if not it.begins_tag(command):
                    # Return the source buffer to the prefix and everything
                    # to initial state
                    sb.set_text(self.hist_prefix)
                    sb.place_cursor(sb.get_end_iter())
                    # Since we change the text and not update the change count,
                    # it's like the user did it and hist_prefix is not longer
                    # meaningful.
                    break
                first_line = self._iter_get_command(it, only_first_line=True)
                if first_line and first_line.startswith(self.hist_prefix):
                    command = self._iter_get_command(it)
                    sb.set_text(command)
                    sb.place_cursor(sb.get_end_iter())
                    self._track_change()
                    tb.move_mark(self.hist_mark, it)
                    break

        else:
            gdk.beep()