# Automated installer for stable-audio-tools on Python 3.12+
#
# stable-audio-tools has broken dependency locks (requires Python < 3.11, PyWavelets==1.4.1).
# This script forces pip to ignore those broken locks and install it anyway, since the 
# underlying code actually works perfectly fine on Python 3.12 once dependencies are satisfied.
#
# Ensure you have run: pip install -r requirements.txt FIRST!

Write-Host "Forcing stable-audio-tools installation (bypassing broken version locks)..."
pip install git+https://github.com/Stability-AI/stable-audio-tools.git --no-deps --ignore-requires-python
Write-Host "Done!"
