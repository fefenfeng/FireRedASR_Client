# FireRedASR_Client

使用**小红书：ASR**搭建的伪实时ASRdemo

模型推理在服务器端通过`websockets`与本地通信, 此repo为本地windows运行客户端

## Usage

`python client_stream_fireredasr.py --config client.cfg`

注意：客户端开启需在服务器端初始化后再开启否则会通信失败



