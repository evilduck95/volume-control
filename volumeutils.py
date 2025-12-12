import psutil
from pulsectl import pulsectl

import windowutils
from loggingutils import get_logger

logger = get_logger(__file__)


class ProcessAudioReference:

    def __init__(self, audio_sink_input: pulsectl.PulseSinkInputInfo, process: psutil.Process):
        self.audio_sink_input = audio_sink_input
        self.process = process


def adjusted_volume_change(requested_change, current_volume) -> float:
    # Already at maximum, I've elected to ignore over-amplification for now
    if requested_change > 0 and current_volume == 1:
        logger.info('Already at max volume')
        return 0
    # Safety first!
    if current_volume + requested_change > 1:
        actual_change = 1 - current_volume
        logger.info('Volume change: ' + str(requested_change) + ' is too high, restricted to ' + str(actual_change))
    else:
        actual_change = requested_change
    return actual_change


def change_sink_input_volume(pulse: pulsectl.Pulse,
                             sink_input: pulsectl.PulseSinkInputInfo,
                             requested_change: float) -> float:
    current_volume = pulse.volume_get_all_chans(sink_input)
    # Check for adjustments over max volume
    actual_change = adjusted_volume_change(requested_change, current_volume)
    # Make the change and report
    pulse.volume_change_all_chans(sink_input, actual_change)
    updated_volume = pulse.volume_get_all_chans(sink_input)
    logger.debug(f'Changed [{sink_input.proplist["application.process.binary"]}] by [{actual_change}] to [{updated_volume}]')
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
        num_of_sink_inputs = len(process_audio_refs)
        logger.info(
            f'Found {num_of_sink_inputs} processes that have audio sinks for: [{parent_proc.pid}:{parent_proc.name()}]')
        if num_of_sink_inputs == 0:
            logger.debug('No Sink Inputs found for process')
            return 0, 'NO_TARGET'
        updated_volume = 0
        # Iterate over Sink Inputs with a ref to a Process related to our focussed Window
        for ref in process_audio_refs:
            logger.info(f'Changing volume for: [{ref.process.pid}:{ref.process.name()}] ')
            proc_new_volume = change_sink_input_volume(pulse, ref.audio_sink_input, change)
            if proc_new_volume > updated_volume:
                updated_volume = proc_new_volume
    # Return the updated volume and the PARENT we found,
    # not necessarily the process we asked about (not 100% on this decision)
    return updated_volume, parent_proc.name()


def change_system_volume(change: float) -> [float]:
    with pulsectl.Pulse('system-volume-editor') as pulse:
        # Get Current Output Device (System volume sink)
        default_sink = pulse.sink_default_get()
        current_volume = pulse.volume_get_all_chans(default_sink)
        actual_change = adjusted_volume_change(change, current_volume)
        pulse.volume_change_all_chans(default_sink, actual_change)
        # Return the volume change and the name of the Device we're editing
        return pulse.volume_get_all_chans(default_sink), default_sink.description
