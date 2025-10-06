# Feature 004: SQLite Tutorial Parity - Getting Started

**Status**: Planning Phase  
**Branch**: `004-sqlitch-tutorial-parity`  
**Created**: October 6, 2025

---

## 🎯 Feature Goal

Implement the minimum command functionality required to complete the Sqitch SQLite tutorial end-to-end using `sqlitch` instead of `sqitch`, achieving identical results.

---

## 📋 What's Been Done

### ✅ Completed
1. **Analyzed Tutorial**: Reviewed all 1,253 lines of `sqitchtutorial-sqlite.pod`
2. **Created Feature Branch**: `004-sqlitch-tutorial-parity`
3. **Written Spec**: `specs/004-sqlitch-tutorial-parity/spec.md`
   - Identified 10 tutorial-critical commands
   - Documented all tutorial workflows
   - Defined 15 functional requirements
   - Listed clarification questions
4. **Created Quickstart**: `specs/004-sqlitch-tutorial-parity/quickstart.md`
   - 8 concrete validation scenarios
   - Full tutorial test script
   - Success metrics and troubleshooting

### 📦 Committed
- Initial spec and quickstart documents committed to feature branch

---

## 🎓 Tutorial Overview

The Sqitch SQLite tutorial demonstrates a complete database change management workflow for a fictional "Flipr" application. It covers:

1. **Project Setup** - Initialize with Git and Sqitch
2. **Basic Workflow** - Add, deploy, verify changes
3. **Dependencies** - Create dependent tables and views
4. **Versioning** - Tag releases
5. **Change Management** - Revert, log, status operations
6. **Advanced Features** - Rework changes with tagged versions

---

## 🔨 Commands Requiring Implementation

### Tutorial-Critical (Must Work)
These 10 commands are used in the tutorial and MUST be functional:

1. **`sqitch init`** - Initialize new project ✅ (stub exists, needs implementation)
2. **`sqitch config`** - Manage configuration (get/set/list)
3. **`sqitch add`** - Add new changes with dependencies
4. **`sqitch deploy`** - Deploy changes to database
5. **`sqitch verify`** - Verify deployed changes
6. **`sqitch revert`** - Revert deployed changes
7. **`sqitch status`** - Show deployment status
8. **`sqitch log`** - Display change history
9. **`sqitch tag`** - Tag releases
10. **`sqitch rework`** - Modify existing changes

### Can Remain Stubs (Not Used in Tutorial)
- `bundle`, `checkout`, `rebase`, `upgrade`, `engine`, `target`, `plan`, `show`

---

## 📊 Implementation Phases (Proposed)

### Phase 1: Foundation (Week 1)
- [ ] **`init`** - Project initialization with config files
- [ ] **`config`** - Get/set/list configuration values
- [ ] Set up integration test framework

### Phase 2: Basic Workflow (Week 2)
- [ ] **`add`** - Create change scripts and update plan
- [ ] **`deploy`** - Execute deploy scripts and record in registry
- [ ] **`verify`** - Execute verify scripts
- [ ] **`status`** - Query and display deployment state

### Phase 3: Change Management (Week 3)
- [ ] **`revert`** - Revert changes with registry updates
- [ ] **`log`** - Display deployment history
- [ ] **`tag`** - Add release tags to plan

### Phase 4: Advanced Features (Week 4)
- [ ] **`rework`** - Create tagged change versions
- [ ] End-to-end tutorial validation
- [ ] Documentation and polish

---

## 🧪 Testing Strategy

### Unit Tests
- Test each command in isolation
- Mock file system, database, registry operations
- ≥90% coverage requirement

### Integration Tests
- Test complete workflows from tutorial scenarios
- Real SQLite databases (in temp directories)
- Validate file generation, database state, registry records

### Parity Tests
- Compare SQLitch output to Sqitch output
- Use golden fixtures from actual Sqitch runs
- Allow for acceptable variations (timestamps, paths)

### Tutorial Validation
- Automated script that runs all 8 quickstart scenarios
- Verifies database state at each step
- Confirms plan and registry integrity

---

## ❓ Open Questions (Need Clarification)

These questions need answers before detailed planning:

1. **Scope**: Implement ALL 10 commands or prioritize subset?
2. **Config depth**: Full config subcommands or basic get/set only?
3. **Target management**: Functional target command or URI-only?
4. **Rework complexity**: Full implementation or minimum viable?
5. **Git integration**: Auto-commit features or manual workflow?
6. **Registry completeness**: All operations or deploy/revert only?

---

## 🚀 Next Steps

### Immediate (You/Agent)
1. **Review spec.md** - Read through the full feature specification
2. **Answer clarifications** - Decide on scope and implementation depth
3. **Update spec** - Remove [NEEDS CLARIFICATION] markers
4. **Run `/plan` command** - Generate research.md and data-model.md
5. **Run `/tasks` command** - Generate detailed task breakdown

### After Planning
1. Create feature branch contracts (test files)
2. Implement commands in priority order
3. Validate against tutorial scenarios
4. Document any deviations from Sqitch behavior

---

## 📁 Project Structure

```
specs/004-sqlitch-tutorial-parity/
├── spec.md              # ✅ Created - Feature specification
├── quickstart.md        # ✅ Created - Validation scenarios
├── research.md          # ⏳ Next - Technical research
├── data-model.md        # ⏳ Next - Data structures
├── plan.md              # ⏳ Next - Implementation plan
├── tasks.md             # ⏳ Later - Detailed task list
└── contracts/           # ⏳ Later - Test contracts
```

---

## 🎯 Success Criteria

Feature 004 is complete when:

- ✅ All 8 quickstart scenarios execute successfully
- ✅ Tutorial test script runs without errors
- ✅ Database state matches expected outcomes
- ✅ Plan and registry databases remain valid
- ✅ Output matches Sqitch (within acceptable variations)
- ✅ Test coverage ≥90% for implemented commands
- ✅ All tests pass in CI pipeline
- ✅ Documentation updated

---

## 📚 Key References

- **Tutorial Source**: `sqitch/lib/sqitchtutorial-sqlite.pod`
- **Feature 002**: SQLite engine implementation (partial)
- **Feature 003**: CLI command parity (✅ complete)
- **Constitution**: `.github/copilot-instructions.md`

---

## 💡 Tips for Implementation

1. **Start Small**: Get `init` and `config` working first
2. **Test Early**: Write integration tests alongside code
3. **Follow Tutorial**: Use tutorial as acceptance test
4. **Match Output**: Byte-for-byte parity with Sqitch default output
5. **Document Deviations**: Any differences from Sqitch must be justified
6. **Maintain Coverage**: Don't let coverage drop below 90%
7. **Use Constitution**: Follow patterns from Features 002/003

---

## 🤝 How to Contribute

1. Review the spec and provide feedback
2. Answer open questions to refine scope
3. Propose implementation approaches
4. Review generated research and data model docs
5. Help with contract test definitions
6. Implement commands following TDD workflow
7. Validate tutorial scenarios

---

**Ready to proceed?** Next step is to answer the clarification questions in `spec.md`, then we can run the `/plan` command to generate detailed research and planning documents.

