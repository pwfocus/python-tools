import sys
import os
import json
import shutil
import hashlib
import paramiko
import requests
from io import BytesIO
from PIL import Image

def cal_md5(file_path):
    # 检查路径是否存在
    if not os.path.exists(file_path):
        return None

    # 确保路径是一个文件，而不是目录
    if not os.path.isfile(file_path):
        return None

    # 计算文件的MD5哈希值
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)

    # 返回MD5哈希值的十六进制表示
    return md5_hash.hexdigest()

def upload(pic_path, config):
    private_key_path = config["private_key_path"]
    hostname = config["hostname"]
    username = config["username"]
    remote_path = config["remote_dir"]

    private_key = paramiko.RSAKey.from_private_key_file(private_key_path)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # 自动添加主机密钥，生产环境请慎用

    try:
        ssh.connect(hostname=hostname, port=22, username=username, pkey=private_key)
        #print(f"Connected to {hostname}")

        # 创建SFTP客户端
        sftp = ssh.open_sftp()
        try:
            # 上传文件到远程路径
            remote_file_path = os.path.join(remote_path, os.path.basename(pic_path))
            sftp.put(pic_path, remote_file_path)
            return True
        finally:
            sftp.close()
    finally:
        ssh.close()
    return False

def convert(pic_path):
    image = Image.open(pic_path)
    if image.format == "PNG":
        jpeg_image = image.convert('RGB')

        # 使用BytesIO保存临时的JPEG数据
        jpeg_io = BytesIO()
        jpeg_image.save(jpeg_io, format="JPEG")
        jpeg_data = jpeg_io.getvalue()
        md5_hash = hashlib.md5(jpeg_data).hexdigest()

        # 获取原始图片所在的目录，并构造输出文件的完整路径
        output_dir = os.path.dirname(pic_path)
        output_path = os.path.join(output_dir, f'{md5_hash}.jpeg')

        # 保存转换后的JPEG图片到文件
        with open(output_path, 'wb') as output_file:
            output_file.write(jpeg_data)

        # 返回转换后的JPEG图片的完整路径
        return output_path
    else:
        return pic_path

def copy_file(pic_path, dst_dir):
    ## 将pic_path移动到一个dst目录下，并按照md5sum.png的方式进行存储
    md5sum = cal_md5(pic_path)
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)

    _, ext = os.path.splitext(pic_path)
    dst_path = os.path.join(dst_dir, f"{md5sum}{ext}")
    shutil.copy2(pic_path, dst_path)
    out_path = convert(dst_path)
    return out_path

def compose_url(pic_path, config):
    hostname = config["hostname"]
    port = config["http_port"]
    filename = os.path.basename(pic_path)
    url = f"http://{hostname}:{port}/assets/{filename}"
    return url

def verify(pic_path, config):
    url = compose_url(pic_path, config)
    response = requests.get(url)
    if response.status_code >= 200 and response.status_code < 400:
        print(url)
        return True

def main():
    # Typora测试的两个文件路径
    # C:\Users\Administrator\AppData\Local\Temp\Typora\typora-icon2.png
    # C:\Users\Administrator\AppData\Local\Temp\Typora\typora-icon.png

    json_file_path = "D:\\python\\config.json"
    with open(json_file_path, 'r') as json_file:
        config = json.load(json_file)

    if len(sys.argv) > 1:
        for pic_path in sys.argv[1:]:
            dst_path = copy_file(pic_path, config["local_assets_dir"])
            upload(dst_path, config)
            verify(dst_path, config)
    else:
        print("no args")

if __name__ == "__main__":
    main()
