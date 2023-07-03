class Chunk3DS:
    """
    Chunk class is a container for holding data relevant to a chunk of a 3DS file.
    """
    __slots__ = ("ID", "length", "bytes_read")

    binary_format = "<HI"  # Binary format for the struct module

    def __init__(self):
        self.ID = 0
        self.length = 0
        self.bytes_read = 0

    def dump(self):
        """
        Function to dump the chunk information.
        """
        print(f'ID: {self.ID}')
        print(f'ID in hex: {hex(self.ID)}')
        print(f'length: {self.length}')
        print(f'bytes_read: {self.bytes_read}')
