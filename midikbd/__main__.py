import argparse

from Xlib.display import Display
from Xlib.ext import xinput, ge
from Xlib import X

import mido

def midi_note_to_string(midi):
    """Convert MIDI note number to music note string. E.g. 28 -> E1"""
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    # I have absolutely no idea how this works, but it does.
    return names[midi % 12] + str((midi - 12) // 12)

def parse_args():
    description = "Use XInput device as MIDI keyboard."
    parser = argparse.ArgumentParser(description=description)

    default_root_note = 36
    help = f"MIDI note number of the lowest note (default: {midi_note_to_string(default_root_note)})"

    parser.add_argument("-r", "--root_note", type=int, default=default_root_note,
                        help=help)

    parser.add_argument("device_id", type=int,
                        help="XInput device ID from `xinput`")
    parser.add_argument("midi_port", type=str,
                        help="name of the MIDI port to be created")

    return parser.parse_args()

def main():
    args = parse_args()

    print("Root note:", midi_note_to_string(args.root_note))

    held_keys = {}

    def is_held(keycode):
        return keycode in held_keys and held_keys[keycode]

    display = Display()

    def establish_grab():
        root = display.screen().root
        time = X.CurrentTime
        async_ = xinput.GrabModeAsync
        mask = xinput.KeyPressMask | xinput.KeyReleaseMask

        root.xinput_grab_device(args.device_id, time, async_, async_, True, mask)

    midi_port = mido.open_output(args.midi_port, virtual=True)
    print(f'Output "{midi_port.name}" open')

    with midi_port:
        establish_grab()
        print("Grabbed device", args.device_id)
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
            # On en_US layout, these are the keys 1-=, Q-], A-\, and Z-/
            # The ranges are inclusive, hence the "+1".

            if keycode in range(10, 21 + 1):
                # Difference from root note.
                # 1 = root note, so 10 - 10 = 0.
                note = keycode - 10
            elif keycode in range(24, 35 + 1):
                # Compensate for 21-24 transition.
                note = keycode - 10 - 2
            elif keycode in range(38, 48 + 1):
                # 21-24 and 35-38 transition.
                note = keycode - 10 - 2 - 2
            elif keycode in range(51, 61 + 1):
                # 21-24, 35-38, and 48-51 transition.
                note = keycode - 10 - 2 - 2 - 2
            else:
                continue

            message.note = note + args.root_note

            midi_port.send(message)

if __name__ == "__main__":
    main()
