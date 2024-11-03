Here's a README.md for your SRT to Audio converter:

```markdown
# SRT to Audio Converter

A Python tool that converts SRT subtitle files into MP3 audio using OpenAI's Text-to-Speech API. This tool maintains precise timing from the original subtitles and supports multiple voice options.

## Features

- Converts SRT subtitles to natural-sounding speech
- Preserves original subtitle timing
- Supports multiple OpenAI voices (alloy, echo, fable, onyx, nova, shimmer)
- Handles silence gaps between subtitles
- Provides detailed progress feedback
- Exports high-quality MP3 files

## Prerequisites

- Python 3.6+
- OpenAI API key
- Required Python packages (install via pip):
  ```bash
  pip install pysrt pydub openai python-dotenv
  ```

## Installation

1. Clone this repository or download the `main.py` file
2. Install the required dependencies
3. Set up your OpenAI API key either in a `.env` file or as an environment variable:
   ```bash
   OPENAI_API_KEY=your-api-key-here
   ```

## Usage

Basic usage:
```bash
python main.py -i subtitles.srt -o output.mp3
```

With different voice:
```bash
python main.py -i subtitles.srt -o output.mp3 -v nova
```

With explicit API key:
```bash
python main.py -i subtitles.srt -o output.mp3 --api-key your-api-key
```

### Command Line Arguments

- `-i, --input`: Input SRT file path (required)
- `-o, --output`: Output MP3 file path (required)
- `-v, --voice`: OpenAI voice to use (default: alloy)
- `--api-key`: OpenAI API key (optional if set via environment variable)

### Available Voices

- `alloy` (default)
- `echo`
- `fable`
- `onyx`
- `nova`
- `shimmer`

## Error Handling

The tool includes comprehensive error handling for:
- Invalid SRT file format
- Missing or invalid API key
- Invalid output paths
- Text-to-speech conversion issues
- File permission problems

## Notes

- The tool includes rate limiting (0.5s delay between API calls)
- Speech segments that exceed their subtitle duration will generate warnings but won't be modified
- The final audio maintains the total duration of the original subtitles

## License

Apache 2.0

## Contributing

[Add contribution guidelines if desired]
```

This README provides a comprehensive overview of your tool's functionality, installation process, and usage instructions. You may want to customize the License and Contributing sections based on your preferences.