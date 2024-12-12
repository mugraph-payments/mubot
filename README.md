# mubot

A [Muchat](https://github.com/mugraph-payments/muchat) and [SimpleX Chat](https://simplex.chat) compatible chat bot that connects to your [ollama](https://ollama.com) instance and chats with you!

## Development

### NixOS

If you are on NixOS (or have Nix installed), you can run this command to get into a shell:

```sh
nix develop
```

If you have `direnv`, running this command will automatically load the environment when you `cd` into the shell:

```sh
direnv allow
```

Then, you can run the application by running:

```sh
mubot ollama <args>
```

Or more directly:

```sh
python -m mubot.ollama -- <args>
```
