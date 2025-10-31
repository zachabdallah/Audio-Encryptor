from flask import Flask, request, send_file
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
matplotlib.use('Agg') #different back end to avoid having to display graphics 
warnings.simplefilter("ignore", WavFileWarning)#scipy doesn't read non-audio chunks which we don't need but it's giving me a warning so we can ignore it.
output_directory = '/Users/zachabdallah/Downloads/xcode/Audio Encryptor/spectrogram_output'
app = Flask(__name__)

def get_permutation(length, password):
    #Create a pseudo-random permutation based on the password
    password_hash = hashlib.sha256(password.encode()).digest()
    seed = int.from_bytes(password_hash, 'big') #"big" for big endian
    rng = np.random.default_rng(seed)
    #print(f"Password: {password}, p_Seed: {seed % 10000}")  #debug log
    permutation = np.arange(length)
    rng.shuffle(permutation)
    return permutation

def get_transforms(shape_frequencies, shape_times, password, frequencies, times):
    #create two randomly generated matrices, one for 'times' and one for 'frequencies'. These matrices will be used to scale the magnitude of the STFT coefficients in Zxx
    password_hash = hashlib.sha256(password.encode()).digest()
    seed = int.from_bytes(password_hash, 'big')
    rng = np.random.default_rng(seed)
    transformation_matrix_frequencies = frequencies * rng.uniform(0.2, 1.3, shape_frequencies)
    #transformation_matrix_frequencies /= np.max(transformation_matrix_frequencies)#normalize
    transformation_matrix_times = times * rng.uniform(0.2, 29, shape_times)
    #transformation_matrix_times /= np.max(transformation_matrix_times)#normalize
    return transformation_matrix_frequencies, transformation_matrix_times

def undo_transforms(shape_frequencies, shape_times, password, frequencies, times):
    #this does the exact opposite of get_transforms, reversing the scaling applied to Zxx
    password_hash = hashlib.sha256(password.encode()).digest()
    seed = int.from_bytes(password_hash, 'big')
    rng = np.random.default_rng(seed)
    transformation_matrix_frequencies = frequencies / rng.uniform(0.2, 1.3, shape_frequencies)
    transformation_matrix_times = times / rng.uniform(0.2, 29, shape_times)
    return transformation_matrix_frequencies, transformation_matrix_times

def shuffle_segments(Zxx, password):
    #This function shuffles the columns of Zxx by rearranging the columns to be ordered according to a permutation derived from the password
    permutation = get_permutation(Zxx.shape[1], password)
    #print("original permutation e\n")
    #print(permutation)
    shuffled_Zxx = Zxx[:, permutation]
    return shuffled_Zxx

def unshuffle_segments(Zxx, permutation):
    #get the reverse permutation and rearrange the columns to be back where they started
    #print("original permutation d\n")
    #print(permutation)
    #print("inverse permutation\n")
    inverse_permutation = np.argsort(permutation)
    #print(inverse_permutation)
    unshuffled_Zxx = Zxx[:, inverse_permutation]
    return unshuffled_Zxx


def modify_Zxx(Zxx, transformation_matrix_frequencies, transformation_matrix_times, password):
    Zxx = shuffle_segments(Zxx, password)
    return Zxx

def undo_modify_Zxx(Zxx, transformation_matrix_frequencies, transformation_matrix_times, permutation):
    #unshuffle segments along the time axis
    Zxx = unshuffle_segments(Zxx, permutation)
    # undo the amplitude transformation, keep phase unchanged
    #Zxx = np.abs(Zxx) / (transformation_matrix_frequencies[:, np.newaxis] * transformation_matrix_times[np.newaxis, :]) * np.exp(1j * np.angle(Zxx))
    return Zxx

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
@app.route('/encrypt', methods=['POST'])
def encrypt():
    try:
        print("\nencryption mode:")
        if 'file' not in request.files:
            return "No file part", 400
        file = request.files['file']
        if file.filename == '':
            return "No selected file", 400
        filepath = os.path.join("/tmp", file.filename)
        file.save(filepath)
        
        password = request.form.get('password')
        if not password:
            return "Password is required for encryption", 400

        #read and process the file
        rate, data = wavfile.read(filepath)
        if len(data.shape) == 2:  # Stereo to mono
            data = np.mean(data, axis=1)
        frequencies, times, Zxx = stft(data, fs=rate, nperseg=1024, noverlap = 512)
        
        #log original values
        print(f"-o_STFT Zxx[10,5]: {Zxx[10, 5]}")
        print(f"-o_Zxx[10,5] magnitude: {np.abs(Zxx[10, 5])}")
        print(f"-o_Zxx[10,5] phase: {np.angle(Zxx[10, 5])}")
        print(f"-o_Zxx shape: {Zxx.shape}")
        #log original files
        save_spectrogram_image(Zxx, times, frequencies, 'Original Spectrogram', original_spectrogram_path)
        wavfile.write(original_audio_path, rate, data.astype(np.int16))

        #apply encryption
        transformation_matrix_frequencies, transformation_matrix_times = get_transforms(Zxx.shape[0], Zxx.shape[1], password, frequencies, times)
        

        Zxx = modify_Zxx(Zxx, transformation_matrix_frequencies, transformation_matrix_times, password)
        _, encrypted_data = istft(Zxx, fs=rate, nperseg=1024,noverlap=512)
        data = encrypted_data.astype(np.int16)
        print("--Frequency matrix during encryption:", transformation_matrix_frequencies[5])
        print("--Time matrix during encryption:", transformation_matrix_times[5])

        #log encrypted values
        print(f"-e_Zxx[10,5]: {Zxx[10, 5]}")
        print(f"-e_Zxx[10,5] magnitude: {np.abs(Zxx[10, 5])}")
        print(f"-e_Zxx[10,5] phase: {np.angle(Zxx[10, 5])}")
        print(f"-e_Zxx shape: {Zxx.shape}")
        

        #log encrypted files
        save_spectrogram_image(Zxx, times, frequencies, 'Modified Spectrogram', modified_spectrogram_path)
        wavfile.write(encrypted_audio_path, rate, data.astype(np.int16))

        return send_file(encrypted_audio_path, as_attachment=True, download_name='encrypted_audio.wav'), 200

    except Exception as e:
        print(f"Encryption failed: {e}")
        return "Internal server error", 500

@app.route('/decrypt', methods=['POST'])
def decrypt():
    try:
        print("\ndecryption mode:")
        if 'file' not in request.files:
            return "No file part", 400
        file = request.files['file']
        if file.filename == '':
            return "No selected file", 400
        filepath = os.path.join("/tmp", file.filename)
        file.save(filepath)
        
        password = request.form.get('password')
        if not password:
            return "Password is required for decryption", 400

        #read and process the file
        rate, data = wavfile.read(filepath)
        frequencies, times, Zxx = stft(data, fs=rate, nperseg=1024, noverlap=512)
        
        #log Encrypted values before decryption
        print(f"d_STFT Zxx[10,5] before decryption: {Zxx[10, 5]}")
        
        #apply decryption
        transformation_matrix_frequencies, transformation_matrix_times = undo_transforms(Zxx.shape[0], Zxx.shape[1], password, frequencies, times)
        permutation = get_permutation(Zxx.shape[1], password)
        restored_Zxx = undo_modify_Zxx(Zxx, transformation_matrix_frequencies, transformation_matrix_times, permutation)
        
        #log restored values
        print(f"-d_Zxx[10,5] after decryption: {restored_Zxx[10, 5]}")
        print(f"-d_Zxx[10,5] magnitude: {np.abs(restored_Zxx[10, 5])}")
        print(f"-d_Zxx[10,5] phase: {np.angle(restored_Zxx[10, 5])}")
        print(f"-d_Zxx shape: {restored_Zxx.shape}")
       

        #check numerical difference
        print(f"Numerical difference at [10,5]: {restored_Zxx[10, 5] - Zxx[10, 5]}")
        if not np.allclose(Zxx, restored_Zxx, atol=1e-6):
            print("Restored Zxx does not match original")
        
        #convert back to time domain
        _, decrypted_data = istft(restored_Zxx, fs=rate, nperseg=1024, noverlap=512)
        data = decrypted_data.astype(np.int16)
       # data = encrypted_data.astype(np.int16)
        print("--Frequency matrix during decryption:", transformation_matrix_frequencies[5])
        print("--Time matrix during decryption:", transformation_matrix_times[5])
        #log restored files
        save_spectrogram_image(restored_Zxx, times, frequencies, 'Restored Spectrogram', restored_spectrogram_path)
        wavfile.write(decrypted_audio_path, rate, data.astype(np.int16))

        return send_file(decrypted_audio_path, as_attachment=True, download_name='decrypted_audio.wav'), 200

    except Exception as e:
        print(f"Decryption failed: {e}")
        return "Internal server error", 500

if __name__ == '__main__':
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    #spectrogram paths
    original_spectrogram_path = f'{output_directory}/original_spectrogram_{timestamp}.png'
    modified_spectrogram_path = f'{output_directory}/modified_spectrogram_{timestamp}.png'
    restored_spectrogram_path = f'{output_directory}/restored_spectrogram_{timestamp}.png'
    #audio paths
    original_audio_path = f'{output_directory}/original_audio_{timestamp}.wav'
    encrypted_audio_path = f'{output_directory}/encrypted_audio_{timestamp}.wav'
    decrypted_audio_path = f'{output_directory}/restored_audio_{timestamp}.wav'
    
    app.run(debug=True)
