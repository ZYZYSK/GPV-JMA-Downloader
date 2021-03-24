sleep 5
cd /mnt/d/Projects/GPV-JMA-Downloader
gnome-terminal --execute bash -i -c "conda activate weather; python main_gpv.py"
gnome-terminal --execute bash -i -c "conda activate weather; python main_sat.py"
gnome-terminal --execute bash -i -c "conda activate weather; python main_rad.py"