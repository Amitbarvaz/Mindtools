class ProgramImportExportService:

    @classmethod
    def export_program(cls, program):
        # Session Title is unique
        # Content Title is unique
        # Session - Content m2m holds data (unique)
        # Chapter Title is unique
        # Module Title is unique
        # Variable name is unique
        # Program title is unique
        # ProgramGoldVariable currently has no unique (prolly should be unique_together on program_id and variable_id)

        # TODO: How to handle files? (especially the dir structure)
        pass

    @classmethod
    def import_program(cls, program):
        pass
