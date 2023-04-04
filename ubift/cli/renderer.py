import logging
import sys
from typing import Dict

from ubift.framework.mtd import Image
from ubift.framework.structs.ubi_structs import UBI_VTBL_RECORD
from ubift.framework.structs.ubifs_structs import UBIFS_DENT_NODE, UBIFS_INODE_TYPES
from ubift.framework.ubi import UBIVolume
from ubift.framework.ubifs import UBIFS


def readable_size(num: int, suffix="B"):
    """
    Converts amount of bytes to a readable format depending on its size.
    Example: 336896B -> 329KiB
    :param num:
    :param suffix:
    :return:
    """
    if num < 0:
        return "-"
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"


def zpad(num: int, len: str) -> int:
    """
    Pads a number with a given amount of zeroes.
    Example: "1" with len of 3 will be padded to 001
    :param num: The number to be padded with zeroes.
    :param len: How many digits the output number will contain, filled with zeroes at the beginning.
    :return: Zero-padded digit.
    """
    len = "0" + str(len)
    return format(num, len)


def render_ubi_instances(image: Image, outfd=sys.stdout) -> None:
    """
    Writes all UBI instances of an Image to stdout in a readable format
    :param image:
    :param outfd:
    :return:
    """
    ubi_instances = []
    for partition in image.partitions:
        if partition.ubi_instance is not None:
            ubi_instances.append(partition.ubi_instance)

    outfd.write(f"UBI Instances: {len(ubi_instances)}\n\n")

    for i,ubi in enumerate(ubi_instances):
        outfd.write(f"UBI Instance {i}\n")
        outfd.write(f"PEB Offset: {ubi.partition.offset // image.block_size}\n")
        outfd.write(f"Physical Erase Blocks: {len(ubi.partition.data) // image.block_size} (start:{ubi.partition.offset} end:{ubi.partition.end})\n")
        outfd.write(f"Volumes: {len(ubi.volumes)}\n")
        for i,vol in enumerate(ubi.volumes):
            outfd.write(f"Volume {vol._vol_num}\n")
            outfd.write(f"Name: {vol.name}\n")
            render_ubi_vtbl_record(vol._vtbl_record, outfd)
        outfd.write(f"\n")


def render_lebs(vol: UBIVolume, outfd=sys.stdout):
    """
    Writes all LEBS to stdout in a readable format
    TODO: Maybe also write ec_hdr or more info in general?
    :param vol:
    :param outfd:
    :return:
    """
    outfd.write(f"UBI Volume Index:{vol._vol_num} Name:{vol.name}\n\n")

    outfd.write("LEB\t--->\tPEB\n")

    lebs = list(vol.lebs.values())
    lebs.sort(key=lambda leb: leb.leb_num)
    for leb in lebs:
        outfd.write(f"{zpad(leb.leb_num,5)}\t--->\t{zpad(leb._peb_num, 5)}\n")


def render_ubi_vtbl_record(vtbl_record: UBI_VTBL_RECORD, outfd=sys.stdout):
    """
    Writes a singel vtbl_record to stdout in a readable format
    :param vtbl_record:
    :param outfd:
    :return:
    """
    outfd.write(f"Reserved PEBs: {vtbl_record.reserved_pebs}\n")
    outfd.write(f"Alignment: {vtbl_record.alignment}\n")
    outfd.write(f"Data Pad: {vtbl_record.data_pad}\n")
    outfd.write(f"Volume Type: {'STATIC' if vtbl_record.vol_type == 2 else 'DYNAMIC' if vtbl_record.vol_type == 1 else 'UNKNOWN'}\n")
    outfd.write(f"Update Marker: {vtbl_record.upd_marker}\n")
    outfd.write(f"Flags: {vtbl_record.flags}\n")
    outfd.write(f"CRC: {vtbl_record.crc}\n")

def render_dents(ubifs: UBIFS, dents: Dict[int, UBIFS_DENT_NODE], full_paths: bool, outfd=sys.stdout) -> None:
    """
    Renders a dict of UBIFS_NODE_DENT to output (like fls in TSK)
    :param ubifs: UBIFS instance, needed to unroll paths
    :param dents: Dict of inode num->dent
    :param full_paths: If True, will print full paths of files
    :param outfd: Where to write output data
    :return:
    """
    dent_list = dents.values() if isinstance(dents, Dict) else dents

    outfd.write("Type\tInode\tName\n")
    for dent in dent_list:
        render_inode_type(dent.type)
        outfd.write(f"\t{dent.inum}\t")
        if full_paths:
            outfd.write(f"{ubifs._unroll_path(dent, dents)}")
        else:
            outfd.write(f"{dent.formatted_name()}")
        outfd.write("\n")

def render_inode_type(inode_type: int, outfd=sys.stdout):
    """
    Renders an UBIFS_INODE_TYPES to a readable format (no newline)
    :param inode_type:
    :return:
    """
    if inode_type == UBIFS_INODE_TYPES.UBIFS_ITYPE_REG:
        outfd.write(f"file")
    elif inode_type == UBIFS_INODE_TYPES.UBIFS_ITYPE_DIR:
        outfd.write(f"dir")
    elif inode_type == UBIFS_INODE_TYPES.UBIFS_ITYPE_LNK:
        outfd.write(f"link")
    elif inode_type == UBIFS_INODE_TYPES.UBIFS_ITYPE_BLK:
        outfd.write(f"blk")
    elif inode_type == UBIFS_INODE_TYPES.UBIFS_ITYPE_CHR:
        outfd.write(f"chr")
    elif inode_type == UBIFS_INODE_TYPES.UBIFS_ITYPE_FIFO:
        outfd.write(f"link")
    elif inode_type == UBIFS_INODE_TYPES.UBIFS_ITYPE_SOCK:
        outfd.write(f"sock")
    else:
        outfd.write(f"unkn")


def render_image(image: Image, outfd=sys.stdout) -> None:
    """
    Writes information about an Image to stdout in a readable format
    :param image:
    :param outfd:
    :return:
    """
    outfd.write(f"MTD Image\n\n")
    outfd.write(f"Size: {readable_size(len(image.data))}\n")

    outfd.write(f"Erase Block Size: {readable_size(image.block_size)}\n")
    outfd.write(f"Page Size: {readable_size(image.page_size)}\n")
    outfd.write(f"OOB Size: {readable_size(image.oob_size)}\n\n")

    outfd.write(f"Physical Erase Blocks: {len(image.data) // image.block_size}\n")
    outfd.write(f"Pages per Erase Block: {image.block_size // image.page_size}\n")
    outfd.write("\n")

    outfd.write(f"Units are in {readable_size(image.block_size)}-Erase Blocks\n")
    mtd_parts = image.partitions

    outfd.write("\tStart\t\t\tEnd\t\t\tLength\t\t\tDescription\n")
    for i, partition in enumerate(mtd_parts):
        start = zpad(partition.offset // image.block_size, 10)
        end = zpad(partition.end // image.block_size, 10)
        length = zpad(len(partition) // image.block_size, 10)
        outfd.write(f"{zpad(i, 3)}:\t{start}\t\t{end}\t\t{length}\t\t{partition.name}\n")

    # TODO: Maybe add a switch if sizes in bytes are prefered?
    # outfd.write("\tStart\t\t\tEnd\t\t\tLength\t\t\tDescription\n")
    # for i,partition in enumerate(mtd_parts):
    #     start = zpad(partition.offset, 10)
    #     end = zpad(partition.end, 10)
    #     length = zpad(len(partition), 10)
    #     outfd.write(f"{zpad(i, 3)}:\t{start}\t\t{end}\t\t{length}\t\t{partition.name}\n")
