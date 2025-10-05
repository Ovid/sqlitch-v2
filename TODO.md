# Identical sqitch behavior out of the box

By default, we should be 100% compatible with sqitch, howeever, we might want
mroe reasonable default for our local project. For example, in our
`sqitch.conf`, we might have this:

    [core]
        engine = sqlite
        compat = sqitch # default behavior if this is missing
        # plan_file = sqitch.plan
        # top_dir = .

But we should be able to:

    sqlitch init myproject \
        --uri https://github.com/user/project/
        --engine sqlite
        --compat sqlitch # only sqlitch or sqitch allowed

At this point, it would create a `sqlitch.conf` file similar to this:

    [core]
        engine = sqlite
        compat = sqlitch # uses sqlitch.* files
        top_dir = sqlitch
        # plan_file = sqlitch/sqlitch.plan
        # deploy_dir = sqlitch/deploy/
        # revert_dir = sqlitch/revert/
        # verify_dir = sqlitch/verify/
        # extension = sql

That avoids the issue where we have a sqitch.conf, sqitch.plan, deploy/, verify/, delete/
all dumped in your top-level directory. Instead, you'll just have a
`sqlicth/conf` and a `sqlitch/` directory, the latter of which contains all of
your files.

# SQLITCH. env variables need to be fixed

# Dups in _seed tests

        modified:   tests/cli/contracts/test_checkout_contract.py
        modified:   tests/cli/contracts/test_deploy_contract.py
        modified:   tests/cli/contracts/test_plan_contract.py
        modified:   tests/cli/contracts/test_rebase_contract.py
        modified:   tests/cli/contracts/test_revert_contract.py
        modified:   tests/cli/test_rework_helpers.py
