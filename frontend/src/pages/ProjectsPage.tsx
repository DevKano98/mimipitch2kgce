import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { MoreHorizontal, Plus } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { api } from "@/lib/api";
import { relativeTime } from "@/lib/time";
import type { Project } from "@/types/api";

type NameDialogState = { kind: "new" | "rename"; project?: Project } | null;

function NameDialog({
  state,
  onClose,
  onConfirm,
}: {
  state: NonNullable<NameDialogState>;
  onClose: () => void;
  onConfirm: (name: string) => Promise<void>;
}) {
  const [value, setValue] = useState(state.project?.title ?? "");
  const title = state.kind === "new" ? "Create project" : "Rename project";
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent aria-describedby="project-dialog-description">
        <DialogTitle>{title}</DialogTitle>
        <DialogDescription id="project-dialog-description">
          Choose a short name you will recognize later.
        </DialogDescription>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            if (value.trim()) void onConfirm(value.trim());
          }}
        >
          <label htmlFor="project-name">Project name</label>
          <input
            autoFocus
            id="project-name"
            className="field"
            value={value}
            maxLength={120}
            onChange={(event) => setValue(event.target.value)}
          />
          <div className="dialog-actions">
            <Button type="button" onClick={onClose}>
              Cancel
            </Button>
            <Button variant="primary" disabled={!value.trim()}>
              {title}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function DeleteDialog({
  project,
  onClose,
  onConfirm,
}: {
  project: Project;
  onClose: () => void;
  onConfirm: () => Promise<void>;
}) {
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogTitle>Delete project</DialogTitle>
        <DialogDescription>
          This permanently removes “{project.title}” and its canvas.
        </DialogDescription>
        <div className="dialog-actions">
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="destructive" onClick={() => void onConfirm()}>
            Delete project
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [nameDialog, setNameDialog] = useState<NameDialogState>(null);
  const [deleteProject, setDeleteProject] = useState<Project | null>(null);
  const navigate = useNavigate();
  useEffect(() => {
    api
      .listProjects()
      .then(setProjects)
      .catch((error: Error) => toast.error(error.message))
      .finally(() => setLoading(false));
  }, []);
  const confirmName = async (title: string) => {
    try {
      if (nameDialog?.kind === "rename" && nameDialog.project) {
        const updated = await api.renameProject(nameDialog.project.id, title);
        setProjects((items) =>
          items.map((item) => (item.id === updated.id ? updated : item)),
        );
        toast.success("Project renamed");
      } else {
        const created = await api.createProject(title);
        navigate(`/p/${created.id}`);
      }
      setNameDialog(null);
    } catch (error) {
      toast.error((error as Error).message);
    }
  };
  const remove = async () => {
    if (!deleteProject) return;
    try {
      await api.deleteProject(deleteProject.id);
      setProjects((items) =>
        items.filter((item) => item.id !== deleteProject.id),
      );
      setDeleteProject(null);
      toast.success("Project deleted");
    } catch (error) {
      toast.error((error as Error).message);
    }
  };

  return (
    <main className="page">
      <div className="projects-shell">
        <header className="projects-header">
          <div>
            <div className="wordmark">Slate</div>
            <p className="subtitle">Think visually. Learn by working it out.</p>
          </div>
          <Button
            variant="primary"
            onClick={() => setNameDialog({ kind: "new" })}
          >
            <Plus size={17} />
            New project
          </Button>
        </header>
        {loading ? (
          <div className="project-grid">
            {[1, 2, 3].map((key) => (
              <div className="skeleton" key={key} />
            ))}
          </div>
        ) : projects.length === 0 ? (
          <section className="empty">
            <h2>Your canvas is ready</h2>
            <p>Create a project, then paste a problem onto the canvas.</p>
            <Button
              variant="primary"
              onClick={() => setNameDialog({ kind: "new" })}
            >
              Create project
            </Button>
          </section>
        ) : (
          <div className="project-grid">
            {projects.map((project) => (
              <article className="card" key={project.id}>
                <Link to={`/p/${project.id}`}>
                  <div className="thumb">
                    {project.has_thumbnail ? (
                      <img
                        src={`/api/projects/${project.id}/thumbnail`}
                        alt=""
                      />
                    ) : (
                      <div className="empty-paper" />
                    )}
                  </div>
                  <div className="card-copy">
                    <div className="card-title">{project.title}</div>
                    <div className="card-meta">
                      Edited {relativeTime(project.updated_at)}
                    </div>
                  </div>
                </Link>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="card-menu"
                      aria-label={`Project actions for ${project.title}`}
                    >
                      <MoreHorizontal size={18} />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent>
                    <DropdownMenuItem
                      onSelect={() =>
                        setNameDialog({ kind: "rename", project })
                      }
                    >
                      Rename
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      className="danger"
                      onSelect={() => setDeleteProject(project)}
                    >
                      Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </article>
            ))}
          </div>
        )}
        {nameDialog && (
          <NameDialog
            key={`${nameDialog.kind}:${nameDialog.project?.id ?? "new"}`}
            state={nameDialog}
            onClose={() => setNameDialog(null)}
            onConfirm={confirmName}
          />
        )}{" "}
        {deleteProject && (
          <DeleteDialog
            project={deleteProject}
            onClose={() => setDeleteProject(null)}
            onConfirm={remove}
          />
        )}{" "}
      </div>
    </main>
  );
}
