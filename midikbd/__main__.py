import sys

from Xlib.display import Display
from Xlib.ext import xinput, ge
from Xlib import X

import mido

def midi_note_to_string(midi):
    """Convert MIDI note number to music note string. E.g. 28 -> E1"""
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    # I have absolutely no idea how this works, but it does.
    return names[midi % 12] + str((midi - 12) // 12)

def print_usage():
    print("Usage:")
    print("  midikbd <device_id> <port_name> <root_note>\n")
    print("Where:")
    print("  device_id - keyboard device ID from `xinput`")
    print("  port_name - the name of the virtual port to be created")
    print("  root_note - MIDI note number the lowest note is assigned")

def parse_args():
    try:
        if len(sys.argv) != 4:
            raise Exception("Provide 3 arguments")
        return (int(sys.argv[1]), sys.argv[2], int(sys.argv[3]))
    except Exception as err:
        print(type(err).__name__, ": ", err, "\n", sep="")
        print_usage()
        sys.exit(1)

def main():
    device_id, port_name, root_note = parse_args()

    print("Root note:", midi_note_to_string(root_note))

    held_keys = {}

    def is_held(keycode):
        return keycode in held_keys and held_keys[keycode]

    display = Display()

    def establish_grab():
        root = display.screen().root
        time = X.CurrentTime
        async_ = xinput.GrabModeAsync
        mask = xinput.KeyPressMask | xinput.KeyReleaseMask

        root.xinput_grab_device(device_id, time, async_, async_, True, mask)

    midi_port = mido.open_output(sys.argv[2], virtual=True)
    print(f'Output "{midi_port.name}" open')

    with midi_port:
        establish_grab()
        print("Grabbed device", device_id)
        print("Press ^C to exit (on grabbed device)")

        while True:
            event = display.next_event()

            # XInput sends generic events only.
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

            # Most likely not portable, but that's not an issue yet.
            # On en_US layout, these are the keys Q-], A-\, and Z-/
            # The ranges are inclusive, hence the "+1".

            if keycode in range(24, 35 + 1):
                # Difference from root note.
                # Q = root note, so 24 - 24 = 0.
                note = keycode - 24
            elif keycode in range(38, 48 + 1):
                # Compensate for 35-38 transition.
                note = keycode - 24 - 2
            elif keycode in range(51, 61 + 1):
                # 35-38 and 48-51 transition.
                note = keycode - 24 - 2 - 2
            else:
                continue

            message.note = note + root_note
            message.velocity = 127 # too quiet otherwise

            midi_port.send(message)

if __name__ == "__main__":
    main()
