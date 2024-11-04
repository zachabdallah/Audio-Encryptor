from flask import Flask, request
from scipy.io import wavfile
from scipy.signal import stft, istft
import numpy as np
import matplotlib.pyplot as plt
import os
import matplotlib
matplotlib.use('Agg') 
import time
import hashlib
import warnings
from scipy.io.wavfile import WavFileWarning
#suppress WavFileWarning
warnings.simplefilter("ignore", WavFileWarning)#scipy doesn't read non-audio chunks which we don't need but it's giving me a warning so we can ignore it.

output_directory = '/Users/zachabdallah/Desktop/UAA/fall 2024/A401/Voice-Recorder-master/spectrogram_output'
app = Flask(__name__)

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

#save a spectrogram as a PNG file
def save_spectrogram_image(Zxx, times, frequencies, title, filename):
    plt.figure()
    plt.pcolormesh(times, frequencies, np.abs(Zxx), shading='gouraud')
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

    #read the WAV file in from Xcode
    rate, data = wavfile.read(filepath)
    
    if len(data.shape) == 2:
        data = np.mean(data, axis=1)

    #retrieve the password from Xcode and define paths
    password = request.form.get('password')
    if not password:
        return "Password is required for encryption", 400

    #spectrogram paths
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    original_spectrogram_path = f'{output_directory}/original_spectrogram_{timestamp}.png'
    encrypted_spectrogram_path = f'{output_directory}/encrypted_spectrogram_{timestamp}.png'
    decrypted_spectrogram_path = f'{output_directory}/decrypted_spectrogram_{timestamp}.png'
    #audio paths
    original_audio_path = f'{output_directory}/original_audio_{timestamp}.wav'
    encrypted_audio_path = f'{output_directory}/encrypted_audio_{timestamp}.wav'
    decrypted_audio_path = f'{output_directory}/decrypted_audio_{timestamp}.wav'

    #STFT algorwhatithm to get the spectrogram 
    frequencies, times, Zxx = stft(data, fs=rate, nperseg=1024)
    #data is the audio signal, fs=rate is the sampling rate, and then nprseg sets the length of each segment to 1024 samples. This parameter affects the frequency and time resolution of the STFT
    #lets clarify. 'frequencies' and 'times' are 1D arrays that correspond to Zxx. Basically, in reference to the bins they will tell you either the center frequencies of each bin  (in 'frequencies') or the center time to the corresponding bin. if Zxx is 10x20, 'frequencies' is 1x10 and 'times' is 1x20.

    #save the original image and audio
    save_spectrogram_image(Zxx, times, frequencies, 'Original Spectrogram', original_spectrogram_path)
    wavfile.write(original_audio_path, rate, data.astype(np.int16))
    #encrypt the spectrogram then save the encrypted image
    encrypted_Zxx = encrypt_spectrogram(Zxx, password)
    save_spectrogram_image(encrypted_Zxx, times, frequencies, 'Encrypted Spectrogram', encrypted_spectrogram_path)
    #Inverse STFT for encrypted audio and save it
    _, encrypted_data = istft(encrypted_Zxx, fs=rate)
    wavfile.write(encrypted_audio_path, rate, encrypted_data.astype(np.int16))
    #decrypt the encrypted spectrogram and reconstruct original audio
    decrypted_Zxx = decrypt_spectrogram(encrypted_Zxx, password)
    save_spectrogram_image(decrypted_Zxx, times, frequencies, 'Decrypted Spectrogram', decrypted_spectrogram_path)
    _, decrypted_data = istft(decrypted_Zxx, fs=rate)
    wavfile.write(decrypted_audio_path, rate, decrypted_data.astype(np.int16))

    return (f"Processing complete. Files saved:\n"
            f"Original Spectrogram (PNG): {original_spectrogram_path}\n"
            f"Encrypted Spectrogram (PNG): {encrypted_spectrogram_path}\n"
            f"Decrypted Spectrogram (PNG): {decrypted_spectrogram_path}\n\n"
            f"Original Audio (WAV): {original_audio_path}\n"
            f"Encrypted Audio (WAV): {encrypted_audio_path}\n"
            f"Decrypted Audio (WAV): {decrypted_audio_path}"), 200

if __name__ == '__main__':
    app.run(debug=True)
