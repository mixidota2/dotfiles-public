return {
  {
    "delphinus/md-render.nvim",
    version = "*",
    cmd = "MdRender",
    dependencies = {
      { "nvim-tree/nvim-web-devicons", version = "*" },
      { "delphinus/budoux.lua", version = "*" },
    },
    keys = {
      {
        "<leader>mp",
        "<Plug>(md-render-preview)",
        desc = "Markdown preview",
      },
      {
        "<leader>ms",
        "<Plug>(md-render-split)",
        desc = "Markdown split preview",
      },
      {
        "<leader>mt",
        "<Plug>(md-render-preview-tab)",
        desc = "Markdown tab preview",
      },
    },
  },
}
