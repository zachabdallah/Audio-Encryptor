from flask import Flask, request
from scipy.io import wavfile
from scipy.signal import stft, istft
import numpy as np
import matplotlib.pyplot as plt
import os
import matplotlib 
import time
import hashlib
import warnings
from scipy.io.wavfile import WavFileWarning
matplotlib.use('Agg')#different back end to avoid having to display graphics 
#suppress WavFileWarning
warnings.simplefilter("ignore", WavFileWarning)#scipy doesn't read non-audio chunks which we don't need but it's giving me a warning so we can ignore it.
output_directory = '/Users/zachabdallah/Desktop/UAA/fall 2024/A401/Voice-Recorder-master/spectrogram_output'
app = Flask(__name__)

def get_permutation(length, password):
    # Create a pseudo-random permutation based on the password
    password_hash = hashlib.sha256(password.encode()).digest()
    seed = int.from_bytes(password_hash, 'big')
    rng = np.random.default_rng(seed)
    permutation = np.arange(length)
    rng.shuffle(permutation)
    return permutation
#get the transformative matrices for both frequencies and times based on the same hash function on the password
def get_transforms(shape_frequencies, shape_times, password):
    password_hash = hashlib.sha256(password.encode()).digest()
    seed = int.from_bytes(password_hash, 'big')
    rng = np.random.default_rng(seed)
    transformation_matrix_frequencies = rng.uniform(0.2, 1.3, shape_frequencies)
    transformation_matrix_times = rng.uniform(0.2, 29, shape_times)
    return transformation_matrix_frequencies, transformation_matrix_times

##pitch modification
def modify_pitch(transformation_matrix_frequencies, frequencies):
    return frequencies * transformation_matrix_frequencies

def undo_modify_pitch(transformation_matrix_frequencies, frequencies):
    return frequencies * transformation_matrix_frequencies

##time modification
def modify_time(transformation_matrix_times, times):
    return times * transformation_matrix_times

def undo_modify_time(transformation_matrix_times, times):
    return times / transformation_matrix_times
##

def shuffle_segments(Zxx, password):
    # Shuffle columns (time segments) of Zxx based on a permutation derived from the password
    permutation = get_permutation(Zxx.shape[1], password)
    shuffled_Zxx = Zxx[:, permutation]
    return shuffled_Zxx, permutation

def unshuffle_segments(Zxx, permutation):
    # Reverse the shuffling based on the stored permutation
    unshuffled_Zxx = np.empty_like(Zxx)
    unshuffled_Zxx[:, permutation] = Zxx
    return unshuffled_Zxx


def modify_Zxx(Zxx, transformation_matrix_frequencies, transformation_matrix_times, password):
    # Transform only the amplitude, keep phase unchanged
    Zxx = np.abs(Zxx) * transformation_matrix_frequencies[:, np.newaxis] * transformation_matrix_times[np.newaxis, :] * np.exp(1j * np.angle(Zxx))

    # Shuffle segments along the time axis with a reversible permutation
    Zxx, permutation = shuffle_segments(Zxx, password)
    return Zxx, permutation

def undo_modify_Zxx(Zxx, transformation_matrix_frequencies, transformation_matrix_times, permutation):
    # Unshuffle segments along the time axis
    Zxx = unshuffle_segments(Zxx, permutation)
    
    # Undo the amplitude transformation, keep phase unchanged
    Zxx = np.abs(Zxx) / (transformation_matrix_frequencies[:, np.newaxis] * transformation_matrix_times[np.newaxis, :]) * np.exp(1j * np.angle(Zxx))
    
    return Zxx



def adjust_times(times, original_order, segment_length=10):
    num_segments = len(original_order)
    segments = [times[i*segment_length:(i+1)*segment_length] for i in range(num_segments)]
    adjusted_segments = [segments[i] for i in original_order]
    return np.concatenate(adjusted_segments)

'''
#convert password into a transformation matrix of the given shape
def password_to_matrix(password, shape):
    password_hash = hashlib.sha256(password.encode()).digest()#creates a SHA-256 hash of the password and returns the raw bytes of the hash. This hash is used as a unique seed for the matrix generation, ensuring that the same password always generates the same matrix. password.encode() converts the string into bytes, which is required for hashing.
    seed = int.from_bytes(password_hash, 'big')#converts bytes into an integer, which serves as a seed for a random number generator stored in big endian which is what 'big' means
    rng = np.random.default_rng(seed)#initialize a random number generator with the seed
    transformation_matrix = rng.uniform(0.5, 1.5, shape)#generate a matrix where each element is uniformly distributed between .5 and 1.5
    #the numbers picked are based on the seeded value of the rng
    return transformation_matrix
#encrypt
def encrypt_spectrogram(Zxx, password):
    #btw, Zxx is the STFT representation of the audio signal where each columns represent time segments and the rows represent frequency bins
    #so like, Zxx[:, 0] contains all of the frequency information at that time slice, and Zxx[0, :] captures how much of a particular frequency is present over time. IT DOES NOT STORE ACTUAL FREQUENCY OR TIME INFORMATION
    #Each entry is a ~complex~ number, which inherently contains two parts (a + bi) which are the amplitude and the phase of the signal. The amplitude is np.abs(Zxx[f, t]) and the phase is np.angle(Zxx[f, t])
    transformation_matrix = password_to_matrix(password, Zxx.shape)
    encrypted_Zxx = Zxx * transformation_matrix
    #literally just multiple the signal matrix by the transformation matrix
    return encrypted_Zxx
#decrypt
def decrypt_spectrogram(encrypted_Zxx, password):
    transformation_matrix = password_to_matrix(password, encrypted_Zxx.shape)
    decrypted_Zxx = encrypted_Zxx / transformation_matrix
    return decrypted_Zxx
'''
#save a spectrogram as a PNG file
def save_spectrogram_image(Zxx, times, frequencies, title, filename):
    plt.figure()

    # Filter Zxx and frequencies to only show up to 3 kHz
    freq_limit = 3000
    freq_indices = frequencies <= freq_limit
    Zxx_limited = Zxx[freq_indices, :]
    frequencies_limited = frequencies[freq_indices]

    # Plot the limited spectrogram
    plt.pcolormesh(times, frequencies_limited, np.abs(Zxx_limited), shading='gouraud')
    plt.title(title)
    plt.xlabel('Time (s)')
    plt.ylabel('Frequency (Hz)')
    plt.colorbar(label='Amplitude')
    plt.savefig(filename)
    plt.close()

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'file' not in request.files:
        return "No file part", 400
    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400
    filepath = os.path.join("/tmp", file.filename)
    file.save(filepath)
    rate, data = wavfile.read(filepath)
    if len(data.shape) == 2:
        data = np.mean(data, axis=1)
    password = request.form.get('password')
    if not password:
        return "Password is required for encryption", 400

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    original_spectrogram_path = f'{output_directory}/original_spectrogram_{timestamp}.png'
    modified_spectrogram_path = f'{output_directory}/modified_spectrogram_{timestamp}.png'
    restored_spectrogram_path = f'{output_directory}/restored_spectrogram_{timestamp}.png'
    #audio paths
    original_audio_path = f'{output_directory}/original_audio_{timestamp}.wav'
    encrypted_audio_path = f'{output_directory}/encrypted_audio_{timestamp}.wav'
    decrypted_audio_path = f'{output_directory}/restored_audio_{timestamp}.wav'
    frequencies, times, Zxx = stft(data, fs=rate, nperseg=1024)
    #data is the audio signal, fs=rate is the sampling rate, and then nprseg sets the length of each segment to 1024 samples. This parameter affects the frequency and time resolution of the STFT
    #lets clarify. 'frequencies' and 'times' are 1D arrays that correspond to Zxx. Basically, in reference to the bins they will tell you either the center frequencies of each bin  (in 'frequencies') or the center time to the corresponding bin. if Zxx is 10x20, 'frequencies' is 1x10 and 'times' is 1x20.

    #print original files
    save_spectrogram_image(Zxx, times, frequencies, 'Original Spectrogram', original_spectrogram_path)
    wavfile.write(original_audio_path, rate, data.astype(np.int16))

    # Generate transformation matrices
    transformation_matrix_frequencies, transformation_matrix_times = get_transforms(Zxx.shape[0], Zxx.shape[1], password)
    #so, these "transformation matrices", which are a 1D array, are randomly generated by the password. We now will simply multiply the 'frequencies' and 'times' arrays to encrypt the data

    # Apply modifications
    Zxx, permutation = modify_Zxx(Zxx, transformation_matrix_frequencies, transformation_matrix_times, password)
    _, modified_data = istft(Zxx, fs=rate) 
    data = modified_data.astype(np.int16)
    #print modified files
    save_spectrogram_image(Zxx, times, frequencies, 'Modified Spectrogram', modified_spectrogram_path)
    wavfile.write(encrypted_audio_path, rate, data.astype(np.int16))

    # Undo modifications to restore original frequencies and times
    Zxx = undo_modify_Zxx(Zxx, transformation_matrix_frequencies, transformation_matrix_times, permutation)
    _, modified_data = istft(Zxx, fs=rate) 
    data = modified_data.astype(np.int16)
    #print reverted files
    save_spectrogram_image(Zxx, times, frequencies, 'Restored Spectrogram', restored_spectrogram_path)
    wavfile.write(decrypted_audio_path, rate, data.astype(np.int16))

    return (f"Files saved:\n"
            f"Original Spectrogram (PNG): {original_spectrogram_path}\n"
            f"Modified Spectrogram (PNG): {modified_spectrogram_path}\n"
            f"Restored Spectrogram (PNG): {restored_spectrogram_path}"), 200

if __name__ == '__main__':
    app.run(debug=True)
