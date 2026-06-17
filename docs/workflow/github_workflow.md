# AI Workflow and Repository Management

To maintain a consistent and safe development environment for all AI agents working on the PRISM project, please follow these guidelines:

## Repositories

- **Frontend**: [Prism-Android-Frontend](https://github.com/Prism-Secure-Contact-App/Prism-Android-Frontend.git)
  - Located at: `Frontend_Source/`
- **Backend**: [Prism-Backend](https://github.com/Prism-Secure-Contact-App/Prism-Backend.git)
  - Located at: `Backend/`

## Branching Strategy

1.  **Never push directly to `main` or `develop` branches.**
2.  For every significant task or feature, create a new branch from the latest state of the default branch.
    - Branch naming convention: `feature/ai-<description>` or `fix/ai-<description>`.
3.  After completing the task, push the branch to GitHub.
4.  Open a Pull Request (PR) for review and merging.
5.  Document important changes in the `docs/` folder to keep other agents and the user informed.

## Task-Specific Notes

- **Frontend**: The project is a rebrand of Element Android. Breez integration is no longer required and should be removed.
- **Backend**: Matrix Synapse based, including bridges for WhatsApp and Meta.
