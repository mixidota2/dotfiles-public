local wezterm = require 'wezterm'
local config = wezterm.config_builder()

config.automatically_reload_config = true
config.font_size = 12.0
config.use_ime = true
config.window_background_opacity = 0.7
config.macos_window_background_blur = 15
config.window_decorations = "RESIZE"
config.hide_tab_bar_if_only_one_tab = true
config.scrollback_lines = 35000
config.color_scheme = "Dracula+"

-- macOSのキーリピート設定
config.enable_kitty_keyboard = false
config.send_composed_key_when_left_alt_is_pressed = false
config.send_composed_key_when_right_alt_is_pressed = true

config.window_frame = {
    inactive_titlebar_bg = "none",
    active_titlebar_bg = "none"
  }
config.window_background_gradient = {
  colors = { "#000000" },
}
config.show_new_tab_button_in_tab_bar = false
config.show_close_tab_button_in_tabs = false
config.colors = {
 tab_bar = {
   inactive_tab_edge = "none",
 },
}

-- =====================================
-- Mac VS Code風キーバインド設定
-- =====================================
config.keys = {
  -- ===== ファイル操作（Mac VS Code風）=====
  -- Cmd+N: 新しいタブ
  {
    key = 'n',
    mods = 'CMD',
    action = wezterm.action.SpawnTab 'CurrentPaneDomain',
  },
  
  -- Cmd+Shift+N: 新しいウィンドウ
  {
    key = 'n',
    mods = 'CMD|SHIFT',
    action = wezterm.action.SpawnWindow,
  },
  
  -- Cmd+W: タブを閉じる
  {
    key = 'w',
    mods = 'CMD',
    action = wezterm.action.CloseCurrentTab { confirm = true },
  },
  
  -- Cmd+Shift+W: ペインを閉じる
  {
    key = 'w',
    mods = 'CMD|SHIFT',
    action = wezterm.action.CloseCurrentPane { confirm = false },
  },

  -- ===== パネル操作（cmux統一）=====
  -- Cmd+D: パネル分割（右）
  {
    key = 'd',
    mods = 'CMD',
    action = wezterm.action.SplitHorizontal { domain = 'CurrentPaneDomain' },
  },

  -- Cmd+Shift+D: パネル分割（下）
  {
    key = 'd',
    mods = 'CMD|SHIFT',
    action = wezterm.action.SplitVertical { domain = 'CurrentPaneDomain' },
  },

  -- Cmd+Option+矢印キー: パネル間移動
  {
    key = 'LeftArrow',
    mods = 'CMD|OPT',
    action = wezterm.action.ActivatePaneDirection 'Left',
  },
  {
    key = 'RightArrow',
    mods = 'CMD|OPT',
    action = wezterm.action.ActivatePaneDirection 'Right',
  },
  {
    key = 'UpArrow',
    mods = 'CMD|OPT',
    action = wezterm.action.ActivatePaneDirection 'Up',
  },
  {
    key = 'DownArrow',
    mods = 'CMD|OPT',
    action = wezterm.action.ActivatePaneDirection 'Down',
  },

  -- ===== タブ操作（Mac VS Code風）=====
  -- Cmd+Shift+]: 次のタブ
  {
    key = '}',
    mods = 'CMD|SHIFT',
    action = wezterm.action.ActivateTabRelative(1),
  },
  
  -- Cmd+Shift+[: 前のタブ
  {
    key = '{',
    mods = 'CMD|SHIFT',
    action = wezterm.action.ActivateTabRelative(-1),
  },
  
  -- Cmd+Shift+矢印キーでタブ切り替え（正しい指定方法）
  {
    key = 'LeftArrow',
    mods = 'CMD|SHIFT',
    action = wezterm.action.ActivateTabRelative(-1),
  },
  {
    key = 'RightArrow',
    mods = 'CMD|SHIFT', 
    action = wezterm.action.ActivateTabRelative(1),
  },
  
  -- 別の方法でタブ切り替え（Ctrl+Tab代替）
  {
    key = 'Tab',
    mods = 'CMD',
    action = wezterm.action.ActivateTabRelative(1),
  },
  
  {
    key = 'Tab',
    mods = 'CMD|SHIFT',
    action = wezterm.action.ActivateTabRelative(-1),
  },
  
  -- Ctrl+数字: 特定のタブに移動（cmux統一）
  {
    key = '1',
    mods = 'CTRL',
    action = wezterm.action.ActivateTab(0),
  },
  {
    key = '2',
    mods = 'CTRL',
    action = wezterm.action.ActivateTab(1),
  },
  {
    key = '3',
    mods = 'CTRL',
    action = wezterm.action.ActivateTab(2),
  },
  {
    key = '4',
    mods = 'CTRL',
    action = wezterm.action.ActivateTab(3),
  },
  {
    key = '5',
    mods = 'CTRL',
    action = wezterm.action.ActivateTab(4),
  },
  {
    key = '6',
    mods = 'CTRL',
    action = wezterm.action.ActivateTab(5),
  },
  {
    key = '7',
    mods = 'CTRL',
    action = wezterm.action.ActivateTab(6),
  },
  {
    key = '8',
    mods = 'CTRL',
    action = wezterm.action.ActivateTab(7),
  },
  {
    key = '9',
    mods = 'CTRL',
    action = wezterm.action.ActivateTab(-1),
  },

  -- ===== Mac VS Code風コマンド・ナビゲーション =====
  -- Cmd+Shift+P: コマンドパレット
  {
    key = 'P',
    mods = 'CMD|SHIFT',
    action = wezterm.action.ActivateCommandPalette,
  },
  -- 代替キーバインド
  {
    key = 'phys:P',
    mods = 'CMD|SHIFT',
    action = wezterm.action.ActivateCommandPalette,
  },
  
  -- Cmd+P: クイックオープン
  {
    key = 'p',
    mods = 'CMD',
    action = wezterm.action.InputSelector {
      title = 'Quick Open',
      choices = {
        { label = '📁 File Manager (Yazi)', id = 'yazi' },
        { label = '📝 Editor (Micro)', id = 'micro' },
        { label = '📊 System Monitor', id = 'htop' },
        { label = '🔍 Git Status', id = 'git' },
        { label = '➕ New Terminal', id = 'new' },
      },
      action = wezterm.action_callback(function(window, pane, id, label)
        if id == 'yazi' then
          pane:send_text('y\n')
        elseif id == 'micro' then
          pane:send_text('micro .\n')
        elseif id == 'htop' then
          pane:send_text('htop\n')
        elseif id == 'git' then
          pane:send_text('git status\n')
        elseif id == 'new' then
          window:perform_action(wezterm.action.SpawnTab 'CurrentPaneDomain', pane)
        end
      end),
    },
  },
  
  -- Cmd+Shift+E: ファイルエクスプローラー（Yazi起動）
  {
    key = 'e',
    mods = 'CMD|SHIFT',
    action = wezterm.action_callback(function(window, pane)
      pane:send_text('y\n')
    end),
  },
  
  -- Cmd+`: ターミナル切り替え（新しいパネル）
  {
    key = '`',
    mods = 'CMD',
    action = wezterm.action.SplitVertical { domain = 'CurrentPaneDomain' },
  },

  -- ===== Mac特有のキーバインド =====
  -- Cmd+,: 設定を開く
  {
    key = ',',
    mods = 'CMD',
    action = wezterm.action_callback(function(window, pane)
      pane:send_text('micro ~/.config/wezterm/wezterm.lua\n')
    end),
  },
  
  -- Cmd+Shift+Q: アプリケーション終了（誤爆防止のためShift追加）
  {
    key = 'q',
    mods = 'CMD|SHIFT',
    action = wezterm.action.QuitApplication,
  },
  
  -- Cmd+M: ウィンドウを最小化
  {
    key = 'm',
    mods = 'CMD',
    action = wezterm.action.Hide,
  },

  -- ===== 検索・ナビゲーション =====
  -- Cmd+F: 検索
  {
    key = 'f',
    mods = 'CMD',
    action = wezterm.action.Search { CaseSensitiveString = '' },
  },
  
  -- Cmd+Control+F: フルスクリーン切り替え
  {
    key = 'f',
    mods = 'CMD|CTRL',
    action = wezterm.action.ToggleFullScreen,
  },

  -- ===== 開発者向けショートカット =====
  -- Cmd+Option+R: 設定リロード
  {
    key = 'r',
    mods = 'CMD|OPT',
    action = wezterm.action.ReloadConfiguration,
  },
  
  -- Cmd+Option+I: デバッグコンソール
  {
    key = 'i',
    mods = 'CMD|OPT',
    action = wezterm.action.ShowDebugOverlay,
  },

  -- ===== プロジェクト・ワークスペース操作 =====
  -- Cmd+Shift+R: ワークスペース切り替え
  {
    key = 'r',
    mods = 'CMD|SHIFT',
    action = wezterm.action.InputSelector {
      title = 'Switch Workspace',
      choices = {
        { label = '🏠 home', id = 'home' },
        { label = '📂 projects', id = 'projects' },
        { label = '⬇️ downloads', id = 'downloads' },
      },
      action = wezterm.action_callback(function(window, pane, id, label)
        local paths = {
          home = '~',
          projects = '~/projects',
          downloads = '~/Downloads',
        }
        
        if paths[id] then
          window:perform_action(
            wezterm.action.SwitchToWorkspace {
              name = label,
              spawn = { cwd = paths[id] }
            },
            pane
          )
        end
      end),
    },
  },
}
 local SOLID_LEFT_ARROW = wezterm.nerdfonts.ple_lower_right_triangle
 local SOLID_RIGHT_ARROW = wezterm.nerdfonts.ple_upper_left_triangle

wezterm.on("format-tab-title", function(tab, tabs, panes, config, hover, max_width)
    local background = "#5c6d74"
    local foreground = "#FFFFFF"
      local edge_background = "none"
    if tab.is_active then
      background = "#ae8b2d"
      foreground = "#FFFFFF"
    end
      local edge_foreground = background
    local title = "   " .. wezterm.truncate_right(tab.active_pane.title, max_width - 1) .. "   "
    return {
        { Background = { Color = edge_background } },
        { Foreground = { Color = edge_foreground } },
        { Text = SOLID_LEFT_ARROW },
       { Background = { Color = background } },
       { Foreground = { Color = foreground } },
      { Text = title },
        { Background = { Color = edge_background } },
        { Foreground = { Color = edge_foreground } },
        { Text = SOLID_RIGHT_ARROW },
    }
   end)

-- 追加のキーバインド（既存の設定を上書きしないように）
table.insert(config.keys, {
  key = 'Enter',
  mods = 'SHIFT',
  action = wezterm.action.SendString('\n')
})

return config
