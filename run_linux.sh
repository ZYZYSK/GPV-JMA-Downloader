sleep 5
SCRIPT_DIR=$(cd $(dirname $0); pwd)
cd $SCRIPT_DIR
gnome-terminal --execute bash -i -c "conda activate weather; python main_gsm.py"
gnome-terminal --execute bash -i -c "conda activate weather; python main_msm.py"
gnome-terminal --execute bash -i -c "conda activate weather; python main_sat.py"
gnome-terminal --execute bash -i -c "conda activate weather; python main_rad.py"