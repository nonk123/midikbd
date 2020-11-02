import sys

from Xlib.display import Display
from Xlib.XK import string_to_keysym
from Xlib.ext import xinput, ge
from Xlib import X

import mido

def print_usage():
    print("Usage:")
    print("  midikbd <device_id> <port_name>\n")
    print("Where:")
    print("  <device_id> - keyboard device ID from `xinput`")
    print("  <port_name> - the name of the virtual port to be created")

def main():
    display = Display()

    try:
        assert len(sys.argv) == 3

        device_id = int(sys.argv[1])

        root = display.screen().root

        root.change_attributes(event_mask = X.KeyPress | X.KeyRelease)
        root.xinput_grab_device(device_id, X.CurrentTime,
                                xinput.GrabModeAsync, xinput.GrabModeAsync, True,
                                xinput.KeyPressMask | xinput.KeyReleaseMask)

        held = False

        with mido.open_ioport(sys.argv[2], virtual=True) as midi_port:
            while True:
                event = display.next_event()

                if event.type != ge.GenericEventCode:
                    continue

                keycode = event.data.detail

                # Hold the note until the key is released.
                if event.evtype == xinput.KeyPress and not held:
                    midi_port.send(mido.Message("note_on", note=keycode))
                    held = True
                elif event.evtype == xinput.KeyRelease:
                    midi_port.send(mido.Message("note_off", note=keycode))
                    held = False
    except Exception as err:
        print("Error: ", err, "\n", sep="")
        print_usage()
        exit(1)
    finally:
        display.close()

if __name__ == "__main__":
    main()
