# Shell Completion

Shell completion is a feature that allows you to press the `Tab` key while typing a command to automatically complete command names, options, and arguments. This can significantly improve your productivity when working with the `imgtools` CLI.

## Generating Completion Scripts

The `imgtools` CLI provides a built-in command to generate shell completion scripts for various shells:

```bash
imgtools shell-completion [SHELL]
```

Where `[SHELL]` is one of: `bash`, `zsh`, or `fish`.

## Installation Instructions

=== "Bash"

    To enable completion for the current bash session:

    ```bash
    source <(imgtools shell-completion bash)
    ```

    For permanent setup, add the completion script to a file in your bash completion directory:

    ```bash
    # Create the completions directory if it doesn't exist
    mkdir -p ~/.bash_completion.d
    
    # Save the completion script to a file
    imgtools shell-completion bash > ~/.bash_completion.d/imgtools
    
    # Add the following to your ~/.bashrc file
    echo 'source ~/.bash_completion.d/imgtools' >> ~/.bashrc
    
    # Reload your shell configuration
    source ~/.bashrc
    ```

=== "Zsh"

    To enable completion for the current zsh session:

    ```zsh
    source <(imgtools shell-completion zsh)
    ```

    For permanent setup:

    ```zsh
    # Create the completions directory if it doesn't exist
    mkdir -p ~/.zsh/completion
    
    # Save the completion script to a file
    imgtools shell-completion zsh > ~/.zsh/completion/_imgtools
    
    # Add to your ~/.zshrc file
    echo 'fpath=(~/.zsh/completion $fpath)' >> ~/.zshrc
    echo 'autoload -U compinit && compinit' >> ~/.zshrc
    
    # Reload your shell configuration
    source ~/.zshrc
    ```

=== "Fish"

    To enable completion for the current fish session:

    ```fish
    imgtools shell-completion fish | source
    ```

    For permanent setup:

    ```fish
    # Create the completions directory if it doesn't exist
    mkdir -p ~/.config/fish/completions
    
    # Save the completion script
    imgtools shell-completion fish > ~/.config/fish/completions/imgtools.fish
    
    # Fish will automatically load the completions on next shell start
    ```

## Verifying Completion Works

After setting up completion, you can verify it works by typing:

```bash
imgtools <TAB>
```

This should display available subcommands. You can also try:

```bash
imgtools dicomsort --<TAB>
```

This should show the `--`options available for the `dicomsort` command 
(i.e `--action`, `--output`, etc.)

## Troubleshooting

If completions don't work after following these steps:

1. Make sure you've reloaded your shell configuration or started a new terminal session
2. Verify that the completion script was properly generated and saved
3. Check if your shell supports tab completion (it should by default)