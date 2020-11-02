import sys
import os

from Xlib.display import Display
from Xlib.ext import xinput, ge
from Xlib import X

import mido

def print_usage():
    print("Usage:")
    print("  midikbd <device_id> <port_name>\n")
    print("Where:")
    print("  device_id - keyboard device ID from `xinput`")
    print("  port_name - the name of the virtual port to be created")

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

        print("Grabbed device", device_id)

        held_keys = {}

        def is_held(keycode):
            return keycode in held_keys and held_keys[keycode]

        with mido.open_output(sys.argv[2], virtual=True) as midi_port:
            print(f'Output "{midi_port.name}" open')
            print("Press ^C to exit (works globally)")

            new_pid = os.fork()

            if new_pid != 0:
                return

            while True:
                event = display.next_event()

                if event.type != ge.GenericEventCode:
                    continue

                keycode = event.data.detail

                # ^C detection.
                if (is_held(37) or is_held(109)) and keycode == 54:
                    break

                # Hold the note until the key is released.
                if event.evtype == xinput.KeyPress and not is_held(keycode):
                    message = mido.Message("note_on")
                    held_keys[keycode] = True
                elif event.evtype == xinput.KeyRelease:
                    message = mido.Message("note_off")
                    held_keys[keycode] = False
                else:
                    continue

                # Ignore notes out of range.
                if keycode >= 0 and keycode <= 127:
                    message.note = keycode
                    midi_port.send(message)
    except Exception as err:
        print("Error: ", err, "\n", sep="")
        print_usage()
        exit(1)
    finally:
        display.close()

if __name__ == "__main__":
    main()
