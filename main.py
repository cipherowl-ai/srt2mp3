import os
from pysrt import open as srt_open
from pydub import AudioSegment
import tempfile
import argparse
from openai import OpenAI
from dotenv import load_dotenv
import time
import sys
from pathlib import Path

class ValidationError(Exception):
    """Custom exception for input validation errors."""
    pass


class SRTToAudio:
    VALID_VOICES = {'alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'}
    
    def __init__(self, api_key, voice="alloy"):
        """
        Initialize the converter with OpenAI API credentials.
        
        Args:
            api_key (str): OpenAI API key
            voice (str): One of the available voices: alloy, echo, fable, onyx, nova, shimmer
            
        Raises:
            ValidationError: If the voice is invalid or API key is empty
        """
        if not api_key or not isinstance(api_key, str) or api_key.isspace():
            raise ValidationError("Invalid API key provided")
            
        if voice not in self.VALID_VOICES:
            raise ValidationError(
                f"Invalid voice '{voice}'. Valid voices are: {', '.join(self.VALID_VOICES)}"
            )
            
        self.client = OpenAI(api_key=api_key)
        self.voice = voice
        self.model = "tts-1"
        self.final_audio = AudioSegment.silent(duration=0)

    def validate_srt_file(self, srt_path):
        """
        Validate SRT file existence and format.
        
        Args:
            srt_path (str): Path to the SRT file
            
        Raises:
            ValidationError: If the file doesn't exist or has invalid format
        """
        if not os.path.exists(srt_path):
            raise ValidationError(f"SRT file not found: {srt_path}")
            
        if not srt_path.lower().endswith('.srt'):
            raise ValidationError(f"Input file must have .srt extension: {srt_path}")
            
        try:
            subtitles = srt_open(srt_path)
            # Try to access the first subtitle to verify format
            next(iter(subtitles))
        except Exception as e:
            raise ValidationError(f"Invalid SRT file format: {str(e)}")
            
    def validate_output_path(self, output_path):
        """
        Validate output path.
        
        Args:
            output_path (str): Path for the output MP3 file
            
        Raises:
            ValidationError: If the output path is invalid
        """
        try:
            # Convert to Path object for better path handling
            output = Path(output_path)
            
            # Check if extension is .mp3
            if output.suffix.lower() != '.mp3':
                raise ValidationError("Output file must have .mp3 extension")
                
            # Check if directory exists or can be created
            output_dir = output.parent
            if not output_dir.exists():
                try:
                    output_dir.mkdir(parents=True)
                except Exception as e:
                    raise ValidationError(f"Cannot create output directory: {str(e)}")
                    
            # Check if file can be written (if it exists, check if it's writable)
            if output.exists() and not os.access(output_path, os.W_OK):
                raise ValidationError(
                    f"Output file exists and is not writable: {output_path}"
                )
                
            # Check if directory is writable
            if not os.access(output_dir, os.W_OK):
                raise ValidationError(f"Output directory is not writable: {output_dir}")
                
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Invalid output path: {str(e)}")
            
    def text_to_speech(self, text):
        """Convert text to speech using OpenAI's TTS API."""
        if not text or text.isspace():
            raise ValidationError("Empty text provided for speech conversion")
            
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            try:
                # Get the response from OpenAI TTS API
                response = self.client.audio.speech.create(
                    model=self.model,
                    voice=self.voice,
                    input=text,
                    response_format="mp3"  # Explicitly request MP3 format
                )
                
                # Write the response content directly to the file
                with open(temp_file.name, 'wb') as f:
                    f.write(response.content)
                
                # Load with specific parameters for consistency
                audio_segment = AudioSegment.from_mp3(
                    temp_file.name,
                    parameters=["-q:a", "0"]  # Use highest quality
                )
                return audio_segment
            except Exception as e:
                raise ValidationError(
                    f"Error in text-to-speech conversion: {str(e)}"
                )
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)

    def process_subtitles(self, srt_file):
        """Process all subtitles and create the final audio."""
        self.validate_srt_file(srt_file)
        current_position = 0
        subtitles = srt_open(srt_file)
        
        # Get total duration from last subtitle
        last_subtitle = list(subtitles)[-1]
        total_duration = (last_subtitle.end.hours * 3600000 +
                         last_subtitle.end.minutes * 60000 +
                         last_subtitle.end.seconds * 1000 +
                         last_subtitle.end.milliseconds)
        
        # Reset subtitles iterator
        subtitles = srt_open(srt_file)
        
        for index, subtitle in enumerate(subtitles, 1):
            try:
                start_time = (subtitle.start.hours * 3600000 +
                            subtitle.start.minutes * 60000 +
                            subtitle.start.seconds * 1000 +
                            subtitle.start.milliseconds)
                
                end_time = (subtitle.end.hours * 3600000 +
                           subtitle.end.minutes * 60000 +
                           subtitle.end.seconds * 1000 +
                           subtitle.end.milliseconds)
                
                print(f"Subtitle {index}:")
                print(f"  Text: {subtitle.text.strip()}")
                print(f"  Start time: {start_time}ms ({subtitle.start})")
                print(f"  End time: {end_time}ms ({subtitle.end})")
                print(f"  Duration: {end_time - start_time}ms")
                print("---")
                
                if end_time <= start_time:
                    print(f"Warning: Invalid timing in subtitle {index}, skipping")
                    continue
                
                # Generate speech for subtitle text
                speech_segment = self.text_to_speech(subtitle.text)
                speech_duration = len(speech_segment)
                
                # Calculate available time until next subtitle
                available_time = end_time - current_position
                
                # If speech is longer than available time, warn but don't modify
                if speech_duration > available_time:
                    print(f"Warning: Speech duration ({speech_duration}ms) exceeds "
                          f"available time ({available_time}ms) for subtitle {index}")
                
                # Add silence before speech if needed
                silence_duration = start_time - current_position
                if silence_duration > 0:
                    self.final_audio += AudioSegment.silent(duration=silence_duration)
                
                # Add speech segment without modification
                self.final_audio += speech_segment
                current_position = current_position + silence_duration + speech_duration
                
            except Exception as e:
                print(f"Error processing subtitle {index}: {str(e)}")
                continue
            
            time.sleep(0.5)  # Rate limiting
        
        # Add final silence if needed
        if current_position < total_duration:
            final_silence = total_duration - current_position
            self.final_audio += AudioSegment.silent(duration=final_silence)

    def export(self, output_path):
        """Export the final audio to an MP3 file."""
        self.validate_output_path(output_path)
        try:
            self.final_audio.export(
                output_path,
                format="mp3",
                parameters=[
                    "-q:a", "0",           # Highest quality
                    "-codec:a", "libmp3lame",  # Use LAME encoder
                    "-b:a", "192k"         # 192kbps bitrate
                ]
            )
        except Exception as e:
            raise ValidationError(f"Error exporting audio file: {str(e)}")


def convert_srt_to_audio(srt_path, output_path, api_key, voice="alloy"):
    """Main function to convert SRT to audio."""
    converter = SRTToAudio(api_key=api_key, voice=voice)
    converter.process_subtitles(srt_path)
    converter.export(output_path)
    print(f"Audio file created successfully: {output_path}")


def validate_api_key(api_key):
    """Validate API key format and presence."""
    if not api_key or not isinstance(api_key, str) or api_key.isspace():
        raise ValidationError(
            "OpenAI API key must be provided either via --api-key argument "
            "or OPENAI_API_KEY environment variable"
        )
    if not api_key.startswith(('sk-', 'org-')):
        raise ValidationError("Invalid OpenAI API key format")


def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser(
        description='Convert SRT subtitles to MP3 audio using OpenAI TTS.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -i subtitles.srt -o output.mp3
  %(prog)s -i subtitles.srt -o output.mp3 -v nova
  %(prog)s -i subtitles.srt -o output.mp3 --api-key your-api-key
        """
    )
    
    parser.add_argument('-i', '--input', 
                       required=True,
                       help='Input SRT file path')
    parser.add_argument('-o', '--output',
                       required=True,
                       help='Output MP3 file path')
    parser.add_argument('-v', '--voice',
                       choices=SRTToAudio.VALID_VOICES,
                       default='alloy',
                       help='OpenAI voice to use (default: alloy)')
    parser.add_argument('--api-key',
                       help='OpenAI API key (can also be set via OPENAI_API_KEY '
                            'environment variable)')

    try:
        args = parser.parse_args()
        
        # Validate API key
        api_key = args.api_key or os.getenv('OPENAI_API_KEY')
        validate_api_key(api_key)
        
        # Convert SRT to audio
        convert_srt_to_audio(args.input, args.output, api_key, args.voice)
        
    except ValidationError as e:
        print(f"Validation Error: {str(e)}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())