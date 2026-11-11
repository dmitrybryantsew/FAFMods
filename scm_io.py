import struct

def pad(size):
    val = 16 - (size % 16)
    return val + 16 if (val < 4) else val

def pad_file(file, s4comment):
    N = pad(file.tell()) - 4
    filldata = b'\xC5\xC5\xC5\xC5\xC5\xC5\xC5\xC5\xC5\xC5\xC5\xC5\xC5\xC5\xC5\xC5'
    file.write(struct.pack(str(N)+'s4s', filldata[0:N], s4comment))
    return file.tell()

def write_scm(filepath, modl, bones, bone_names, verts, faces, info=None):
    with open(filepath, 'w+b') as f:
        f.write(struct.pack('4s11I', *modl))

        pad_file(f, b'NAME')
        for name in bone_names:
            f.write(struct.pack(f'{str(len(name))}sx', name))
        pad_file(f, b'SKEL')
        bone_offset = f.tell()
        f.write(struct.pack('16f3f4f4i' * (len(bones) // 27), *bones))
        pad_file(f, b'VRTX')
        vert_offset = f.tell()
        f.write(struct.pack('3f3f3f3f2f2f4B' * (len(verts) // 20), *verts))
        pad_file(f, b'TRIS')
        face_offset = f.tell()
        f.write(struct.pack('H' * len(faces), *faces))

        # Rewrite MODL header with true offsets to prevent any alignment drift
        f.seek(0)
        true_modl = [
            modl[0], modl[1],
            bone_offset, modl[3],
            vert_offset, modl[5], modl[6],
            face_offset, modl[8],
            modl[9], modl[10], modl[11]
        ]
        f.write(struct.pack('4s11I', *true_modl))

def write_sca(filepath, anim, names, links, frames):
    with open(filepath, 'w+b') as f:
        f.write(struct.pack('4siifiiiii', *anim))
        pad_file(f, b'NAME')
        f.write(struct.pack(str(len(names)) + 's', names.encode('ascii')))
        pad_file(f, b'LINK')
        f.write(struct.pack(str(len(links)) + 'i', *links))
        pad_file(f, b'DATA')
        # Mandatory 28-byte dummy root pose required by Supreme Commander / FAF engine
        f.write(struct.pack('<7f', 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0))
        f.write(struct.pack(f'fi{7 * len(links)}f' * (len(frames) // (7 * len(links) + 2)), *frames))
