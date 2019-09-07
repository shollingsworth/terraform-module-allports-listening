############################################################################
# DATA
############################################################################
locals {
  zipfile = "${path.module}/.zip/files.zip"
}

data "archive_file" "init_dir" {
  type        = "zip"
  source_dir  = "${path.module}/files"
  output_path = "${local.zipfile}"
}
