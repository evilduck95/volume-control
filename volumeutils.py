import psutil
from pulsectl import pulsectl

import windowutils
from loggingutils import get_logger

last_controlled_media = ""

logger = get_logger(__file__)


class ProcessAudioReference:

    def __init__(self, audio_sink_input: pulsectl.PulseSinkInputInfo, process: psutil.Process):
        self.audio_sink_input = audio_sink_input
        self.process = process


def adjusted_volume_change(requested_change, current_volume) -> float:
    # Already at maximum, I've elected to ignore over-amplification for now
    if requested_change > 0 and current_volume == 1:
        print('Already at max volume')
        return 0
    # Safety first!
    if current_volume + requested_change > 1:
        actual_change = 1 - current_volume
        print('Volume change: ' + str(requested_change) + ' is too high, restricted to ' + str(actual_change))
    else:
        actual_change = requested_change
    return actual_change


# TODO: To handle multiple processes, we need to be able to scale the entire apps audio
def change_sink_input_volume(pulse: pulsectl.Pulse,
                             sink_input: pulsectl.PulseSinkInputInfo,
                             requested_change: float) -> float:
    current_volume = pulse.volume_get_all_chans(sink_input)
    # Check for adjustments over max volume
    actual_change = adjusted_volume_change(requested_change, current_volume)
    # Make the change and report
    pulse.volume_change_all_chans(sink_input, actual_change)
    updated_volume = pulse.volume_get_all_chans(sink_input)
    # print('Changed volume of app by: ' + str(actual_change) + '. New Volume: ' + str(updated_volume))
    return updated_volume


def change_active_window_volume_v2(change: float) -> [float, str]:
    process_audio_refs = []
    parent_proc, child_procs = windowutils.find_focused_app_process_ids()
    all_active_window_procs = [parent_proc, *child_procs]
    with pulsectl.Pulse('focused_app_volume') as pulse:
        # Gather Sink Inputs and Processes together
        for sink_input in pulse.sink_input_list():
            for proc in all_active_window_procs:
                app_id = sink_input.proplist['application.process.id']
                if app_id == str(proc.pid):
                    proc_audio = ProcessAudioReference(sink_input, proc)
                    process_audio_refs.append(proc_audio)
        logger.info(f'Found {len(process_audio_refs)} processes that have audio sinks for: [{parent_proc.pid}:{parent_proc.name()}]')
        updated_volume = 0
        # Iterate over Sink Inputs with a ref to a Process related to our focussed Window
        for ref in process_audio_refs:
            logger.info(f'Changing volume for: [{ref.process.pid}:{ref.process.name()}] ')
            proc_new_volume = change_sink_input_volume(pulse, ref.audio_sink_input, change)
            if proc_new_volume > updated_volume:
                updated_volume = proc_new_volume
    return updated_volume, parent_proc.name()


def change_active_window_volume(change: float) -> [float, str]:
    global last_controlled_media
    active_pid, window_name = windowutils.get_active_window_info()
    with pulsectl.Pulse('focused-application-volume-editor') as pulse:
        for sink_input in pulse.sink_input_list():
            app_id = sink_input.proplist['application.process.id']
            # print('Next Sink Input: ' + str(app_id))
            if app_id == str(active_pid).strip():
                # print('Found Application: ' + sink_input.proplist['application.name'] +
                #       ', matching PID: ' + str(active_pid))
                media_name = sink_input.proplist['media.name']
                if media_name != last_controlled_media:
                    last_controlled_media = media_name
                    print('Media: ' + media_name)
                return change_sink_input_volume(pulse, sink_input, change), media_name
    # Default values to return in event we're focused on a silent app
    return 0, 'NO_TARGET'


def change_system_volume(change: float) -> [float]:
    with pulsectl.Pulse('system-volume-editor') as pulse:
        # Get Current Output Device (System volume sink)
        default_sink = pulse.sink_default_get()
        current_volume = pulse.volume_get_all_chans(default_sink)
        actual_change = adjusted_volume_change(change, current_volume)
        pulse.volume_change_all_chans(default_sink, actual_change)
        return pulse.volume_get_all_chans(default_sink), default_sink.description
